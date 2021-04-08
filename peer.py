if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p',
        '--peer',
        action='append',
        default=[],
        dest='peers',
        help='initial peers to connect to',
        metavar='PEER',
        type=str,
    )
    parser.add_argument(
        '--port',
        default=5555,
        help='port to listen on',
        type=int,
    )
    args = parser.parse_args()

    import asyncio
    import json

    peers = []

    class DiscoveryProtocol(asyncio.DatagramProtocol):
        def connection_made(self, transport):
            self.transport = transport

            for peer in args.peers:
                peers.append(('127.0.0.1', int(peer)))

            add_peer_msg = json.dumps({'action': 'add-peer'}).encode('utf-8')
            request_peer_msg = json.dumps({'action': 'request-peers'}).encode('utf-8')

            for peer in peers:
                self.transport.sendto(add_peer_msg, peer)
                self.transport.sendto(request_peer_msg, peer)

        def datagram_received(self, data, addr):
            try:
                data = json.loads(data)
            except:
                print('Invalid message received from {}'.format(addr))
                return

            if not isinstance(data, dict):
                print('Invalid message received from {}'.format(addr))
                return

            action = data.get('action')

            if not action:
                print('Invalid message received from {}'.format(addr))
                return

            if action == 'add-peer':
                peers.append(addr)

            elif action == 'request-peers':
                print('request-peers')
                self.transport.sendto(
                    json.dumps({
                        'action': 'respond-peers',
                        'peers': ['{}:{}'.format(*peer) for peer in peers],
                    }).encode('utf-8'),
                    addr,
                )

            elif action == 'respond-peers':
                print('respond-peers')
                print(data)
                for p in data.get('peers',[]):
                    phost, pport = p.split(':')
                    pport = int(pport)
                    peer = (phost, pport)
                    if not peer in peers:
                        peers.append(peer)
                        print('Added peer {}'.format(peer))
                        add_peer_msg = json.dumps({'action': 'add-peer'}).encode('utf-8')
                        self.transport.sendto(add_peer_msg, peer)

            else:
                print('Unknown action {}'.format(action))

    loop = asyncio.get_event_loop()
    t = loop.create_datagram_endpoint(
        DiscoveryProtocol,
        local_addr=('0.0.0.0', args.port),
    )
    loop.run_until_complete(t)
    print('Running on port {}'.format(args.port))
    loop.run_forever()
