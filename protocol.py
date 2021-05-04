from abc import abstractmethod
from datetime import datetime, timezone
from typing import cast, Generic, Tuple, TypeVar
import asyncio

import encoders

M = TypeVar('M')

class BaseDatagramProtocol(asyncio.DatagramProtocol, Generic[M]):
    def __init__(self, encoder: encoders.BaseEncoder[M]):
        self.encoder = encoder

    def __call__(self):
        return self

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, data:bytes, sender:Tuple[str,int]) -> None:
        message = self.get_encoder().decode(data)
        self.receive(message, sender)

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        print("Connection closed")
        self.on_con_lost.set_result(True)

    def send(self, message:M, recipient:Tuple[str,int]) -> None:
        data = self.get_encoder().encode(message)
        self._transport.sendto(data, recipient)

    def get_encoder(self) -> encoders.BaseEncoder[M]:
        return self.encoder

    @abstractmethod
    def receive(self, message:M, sender:Tuple[str,int]) -> None:
        raise NotImplementedError(self.__class__.__name__ + '.receive')

class PeerProtocol(BaseDatagramProtocol[dict]):
    def __init__(self, encoder):
        super().__init__(encoder)
        self.peers = {}

    def connection_made(self, transport:asyncio.BaseTransport):
        super().connection_made(transport)

        for peer in self.peers:
            print('Connecting to peer {}'.format(peer))
            self.send(
                {
                    'action': 'peer:add',
                    'mutual': True,
                },
                peer,
            )

    def receive(self, message:dict, sender:Tuple[str,int]) -> None:
        action = message.get('action')

        if not action:
            return

        if action == 'peer:add':
            mutual_p = message.get('mutual?', False)

            if not sender in self.peers:
                self.add_peer(sender, mutual_p)

            self.send({ 'action': 'peer:ack-add', 'added?': True }, sender)

        if sender in self.peers:
            self.peers[sender]['seen-utc'] = datetime.now(timezone.utc)
        else:
            return

        if action == 'peer:ack-add':
            added_p = message.get('added?', False)

            self.peers[sender]['mutual?'] = added_p

        if action == 'peer:beat':
            self.send({ 'action': 'peer:ack-beat'}, sender)

        if action == 'peer:ack-beat':
            # The purpose of this is to set seen-utc, which is already done above
            pass

    def add_peer(self, peer:Tuple[str,int], mutual_p:bool=False):
        print('Adding peer {}'.format(peer))
        self.peers[peer] = {
            'mutual?': mutual_p,
            'seen-utc': datetime.now(timezone.utc),
        }

if __name__ == '__main__':
    import asyncio
    import json
    import socket
    import unittest
    from unittest.mock import Mock

    import encoders

    class BaseDatagramProtocolTests(unittest.TestCase):
        def test_call_returns_self(self):
            '''
            This is needed because of how asyncio instantiates the protocol.
            '''
            p0 = BaseDatagramProtocol()
            p1 = p0()
            assert p0 is p1

        def test_get_encoder_returns_encoder(self):
            sentinel = object()

            class P(BaseDatagramProtocol[str]):
                def __init__(self):
                    super().__init__()
                    self.encoder = sentinel

            p = P()
            assert p.get_encoder() is sentinel

        def test_send_calls_transport(self):
            encoded_message = b'encoded message'
            unencoded_message = 'unencoded message'
            message_destination = ('1.2.3.4', 555)

            encoder = Mock()
            encoder.encode.return_value = encoded_message

            transport = Mock()

            class P(BaseDatagramProtocol[str]):
                def __init__(self):
                    super().__init__()
                    self.encoder = encoder

            p = P()
            p.connection_made(transport)
            p.send(unencoded_message, message_destination)

            encoder.encode.assert_called_with(unencoded_message)
            transport.sendto.assert_called_with(encoded_message, message_destination)

        def test_datagram_received_calls_receive(self):
            encoded_message = b'encoded message'
            decoded_message = 'decoded message'
            message_source = ('1.2.3.4', 555)

            encoder = Mock()
            encoder.decode.return_value = decoded_message

            recorder = Mock()

            class P(BaseDatagramProtocol[str]):
                def __init__(self):
                    super().__init__()
                    self.encoder = encoder

                def receive(self, message, source):
                    recorder.record(message, source)

            p = P()
            p.datagram_received(encoded_message, message_source)

            encoder.decode.assert_called_with(encoded_message)
            recorder.record.assert_called_with(decoded_message, message_source)

    class PeerProtocolTests(unittest.TestCase):
        def setUp(self):
            self.peer_address = ('0.0.0.0', 555)

        # TODO Make these tests test the calling of send() rather than transport.sendto()
        def test_if_no_action_does_not_respond(self):
            encoder = Mock()
            transport = Mock()

            p = PeerProtocol(encoder)
            p.connection_made(transport)
            p.receive({}, ('0.0.0.0', 555))

            transport.sendto.assert_not_called()

        def test_peer_add_responds_with_added_true(self):
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.receive({'action': 'peer:add'}, ('0.0.0.0', 555))

            transport.sendto.assert_called_once_with(
                b'{"action":"peer:ack-add","added?":true}',
                ('0.0.0.0', 555),
            )

        def test_peer_add_adds_peer(self):
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.receive({'action': 'peer:add'}, ('0.0.0.0', 555))

            assert ('0.0.0.0', 555) in p.peers

        def test_peer_add_sets_seen_utc(self):
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.receive({'action': 'peer:add'}, ('0.0.0.0', 555))

            assert p.peers[('0.0.0.0', 555)]['seen-utc']

        def test_if_not_peer_ack_add_does_nothing(self):
            # TODO Don't set the peer directly
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.receive({'action': 'peer:ack-add', 'added?': True}, ('0.0.0.0', 555))

            assert ('0.0.0.0', 555) not in p.peers

        def test_ack_add_sets_peer_to_mutual_if_added_p_true(self):
            # TODO Don't set the peer directly
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.peers[('0.0.0.0', 555)] = {
                'mutual?': False,
            }
            p.receive({'action': 'peer:ack-add', 'added?': True}, ('0.0.0.0', 555))

            assert p.peers[('0.0.0.0', 555)]['mutual?']

        def test_ack_add_does_not_set_peer_to_mutual_if_added_p_false(self):
            # TODO Don't set the peer directly
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.peers[('0.0.0.0', 555)] = {
                'mutual?': False,
            }
            p.receive({'action': 'peer:ack-add', 'added?': False}, ('0.0.0.0', 555))

            assert p.peers[('0.0.0.0', 555)]['mutual?'] is False

        def test_ack_add_sets_seen_utc(self):
            # TODO Don't set the peer directly
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.peers[('0.0.0.0', 555)] = {
                'mutual?': False,
            }
            p.receive({'action': 'peer:ack-add', 'added?': False}, ('0.0.0.0', 555))

            assert p.peers[('0.0.0.0', 555)]['seen-utc']

        def test_if_not_peer_heartbeat_does_nothing(self):
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.receive({'action': 'peer:beat' }, self.peer_address)

            transport.sendto.assert_not_called()
            assert self.peer_address not in p.peers

        def test_if_peer_hearbeat_returns_ack(self):
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.peers[self.peer_address] = {
                'mutual?': False,
            }
            p.receive({'action': 'peer:beat' }, self.peer_address)

            transport.sendto.assert_called_once_with(
                b'{"action":"peer:ack-beat"}',
                self.peer_address,
            )

        def test_heartbeat_sets_seen_utc(self):
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.peers[self.peer_address] = {
                'mutual?': False,
            }
            p.receive({'action': 'peer:beat' }, self.peer_address)

            assert p.peers[self.peer_address]['seen-utc']

        def test_if_not_peer_ack_beat_does_nothing(self):
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.receive({'action': 'peer:ack-beat' }, self.peer_address)

            transport.sendto.assert_not_called()
            assert self.peer_address not in p.peers

        def test_ack_beat_sets_seen_utc(self):
            transport = Mock()

            p = PeerProtocol(encoders.JsonEncoder())
            p.connection_made(transport)
            p.peers[self.peer_address] = {
                'mutual?': False,
            }
            p.receive({'action': 'peer:ack-beat' }, self.peer_address)

            assert p.peers[self.peer_address]['seen-utc']

    unittest.main()
