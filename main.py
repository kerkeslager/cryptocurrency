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

import peer
peer.UDPSwarm(port=args.port).run(
    init_peers=[('127.0.0.1', int(peer_port)) for peer_port in args.peers],
)
