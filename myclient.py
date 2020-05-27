import socket as Socket

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = Socket.socket(Socket.AF_INET, Socket.SOCK_STREAM)
    
    def connect(self):
        self.socket.connect((self.host, self.port))

    def test_send(self):
        self.socket.sendall(b'Hello, world')

    def receive(self):
        self.socket.recv(1024)
        


if __name__ == "__main__":
    client = Client("127.0.0.1", 1200)