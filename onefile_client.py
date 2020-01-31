import socket, platform, sys, os, threading, time

class Client:
    def __init__(self, port):
        self.socket = socket.socket()
        self.server_host = "localhost"
        self.port = port
        self.buffer = 1024

        self.decode_utf8 = lambda data: data.decode("utf-8") # function to receive and decrypt data
        self.receive = lambda buffer: self.socket.recv(buffer) # function to receive and decrypt data
        self.send = lambda data: self.socket.send(data) # function to send encrypted data

        thread = threading.Thread(target=self.connect)
        thread.start()
        self.main()

    def connect(self):
        while True:  # infinite loop until socket can connect
            try:
                self.socket = socket.socket()
                self.socket.connect((self.server_host, self.port))
            except socket.error: time.sleep(5)  # wait 5 seconds to try again
            else: break

            userInfo = socket.gethostname() + "||" + platform.system() + " " + platform.release()
            self.send(str.encode(userInfo))

    def main(self):
        while True:
            try:
                while True:
                    strData = self.socket.recv(self.buffer)
                    strData = self.decode_utf8(strData)

                    if strData == "test": 
                        print("Got test")
                        self.send(str.encode("hello"))
            except socket.error:
                self.socket.close()
                del self.socket
                self.connect()

Client(int(sys.argv[1]))
