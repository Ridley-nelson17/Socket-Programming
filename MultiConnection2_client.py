import socket
import pickle5 as pickle
import math

HEADER_SIZE = 4
HOST = "127.0.0.1"
PORT = 12001

den = 20
rad = 100
theta = math.tau / den

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((HOST, PORT)) #connect to server

    for step in range(1000):
        i = step%den
        x = math.cos(i*theta) * rad
        y = math.sin(i*theta) * rad
        # data = pickle.dumps((x, y), protocol=0)
        data = b"hello world"
        # compute header by taking the byte representation of the int
        header = len(data).to_bytes(HEADER_SIZE, byteorder ='big')
        sock.sendall(header + data)