import argparse
import asyncio

import protocol

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
    default=555,
    help='port to listen on',
    type=int,
)
args = parser.parse_args()

loop = asyncio.get_event_loop()
udp_listener = loop.create_datagram_endpoint(
    protocol.EchoProtocol(),
    local_addr=('0.0.0.0', args.port),
)
loop.run_until_complete(udp_listener)
loop.run_forever()
