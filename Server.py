#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback
import libserver

sel = selectors.DefaultSelector()

clients = libserver.Clients()

def accept_connection(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print("[CONNECTION STATUS]: Connecting to:", addr)
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, data=libserver.Message(sel, conn, addr))
    clients.clients.append(sock)

if len(sys.argv) != 3:
    print("usage:", sys.argv[0], "<host> <port>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Avoid bind() exception: OSError: [Errno 48] Address already in use
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen(0)
print("listening on", (host, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None: accept_connection(key.fileobj)
            else:
                pipe = key.data
                try: pipe.process_events(mask)
                except Exception:
                    print("[SERVER] error: exception for", f"{pipe.addr}:\n{traceback.format_exc()}")
                    pipe.close()
        
except KeyboardInterrupt: print("[SERVER]: caught keyboard interrupt, exiting")
finally: sel.close()