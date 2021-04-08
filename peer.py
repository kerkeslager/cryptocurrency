from typing import Callable, List, Tuple
import asyncio
import json

def json_encode(data):
    return json.dumps(data).encode('utf-8')

def json_decode(data):
    return json.loads(data)

class Protocol(asyncio.DatagramProtocol):
    def __init__(self, on_connect, handler):
        self.on_connect = on_connect
        self.handler = handler

    def connection_made(self, transport):
        self.transport = transport
        self.on_connect(self.transport)

    def datagram_received(self, data, addr):
        self.handler(self.transport, addr, data)

    def __call__(self):
        return self

def send(transport, address, data):
    data = json_encode(data)
    print('Sending to {}: {}'.format(address, data))
    transport.sendto(data, address)

class UDPSwarm(object):
    def __init__(self, port:int):
        self.port = port
        self.peers = []

    def add_peer(self, peer):
        host, port = peer
        if port == self.port:
            return False

        if peer in self.peers:
            return False

        self.peers.append(peer)
        print('Added peer {}'.format(peer))
        return True

    def message_handler(self, transport, addr, data):
        try:
            data = json_decode(data)
        except:
            print('Invalid message received from {}'.format(addr))
            return

        if not isinstance(data, dict):
            print('Invalid message received from {}'.format(addr))
            return

        print('Received from {}: {}'.format(addr, data))

        action = data.get('action')

        if not action:
            print('Invalid message received from {}'.format(addr))
            return

        if action == 'add-peer':
            self.add_peer(addr)

        elif action == 'request-peers':
            transport.sendto(
                json_encode({
                    'action': 'respond-peers',
                    'peers': ['{}:{}'.format(*peer) for peer in self.peers],
                }),
                addr,
            )

        elif action == 'respond-peers':
            for p in data.get('peers',[]):
                phost, pport = p.split(':')
                pport = int(pport)
                peer = (phost, pport)

                was_added = self.add_peer(peer)
                if was_added:
                    send(transport, peer, {'action': 'add-peer'})

        else:
            print('Unknown action {}'.format(action))

        print('Peers: {}'.format(self.peers))

    def run(self, init_peers:List[Tuple[str, int]]) -> None:
        def on_connect(transport):
            for peer in init_peers:
                print('Attempting to add peer {}'.format(peer))
                send(transport, peer, {'action': 'add-peer'})
                send(transport, peer, {'action': 'request-peers'})
                self.add_peer(peer)

        loop = asyncio.get_event_loop()
        t = loop.create_datagram_endpoint(
            Protocol(on_connect, self.message_handler),
            local_addr=('0.0.0.0', self.port),
        )
        loop.run_until_complete(t)
        print('Running on port {}'.format(self.port))
        loop.run_forever()
