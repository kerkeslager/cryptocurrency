if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--peer', type=str, action='append', dest='peers', metavar='PEER', help='initial peers to connect to')
    parser.add_argument('--port', type=int, default=5555, help='port to listen on')
    args = parser.parse_args()

    import selectors
    import socket

    sel = selectors.DefaultSelector()

    def accept(sock, mask):
        conn, addr = sock.accept()  # Should be ready
        print('accepted', conn, 'from', addr)
        conn.setblocking(False)
        sel.register(conn, selectors.EVENT_READ, read)

    def read(conn, mask):
        data = conn.recv(1024)  # Should be ready
        if data:
            print('echoing', repr(data), 'to', conn)
            conn.send(data)  # Hope it won't block
        else:
            print('closing', conn)
            sel.unregister(conn)
            conn.close()

    sock = socket.socket()
    sock.bind(('localhost', args.port))
    sock.listen(100)
    sock.setblocking(False)
    sel.register(sock, selectors.EVENT_READ, accept)

    while True:
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)
