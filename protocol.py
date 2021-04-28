from abc import abstractmethod
from typing import Generic, Tuple, TypeVar
import asyncio

import encoders

M = TypeVar('M')

class BaseDatagramProtocol(asyncio.DatagramProtocol, Generic[M]):
    def __call__(self):
        return self

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self._transport = transport

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

    def get_encoder(self):
        if not hasattr(self, 'encoder'):
            raise NotImplementedError(
                'Must implement {} or {}'.format(
                    self.__class__.__name__ + '.encoder',
                    self.__class__.__name__ + '.get_encoder()'
                ),
            )

        return self.encoder

    @abstractmethod
    def receive(self, message:M, sender:Tuple[str,int]) -> None:
        raise NotImplementedError(self.__class__.__name__ + '.receive')

if __name__ == '__main__':
    import asyncio
    import json
    import socket
    import unittest
    from unittest.mock import Mock

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

    unittest.main()
