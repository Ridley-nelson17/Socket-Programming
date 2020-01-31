import socket, platform, sys, os, threading, time

class Client:
    def __init__(self, port):
        self.socket = None #socket.socket()
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
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.server_host, self.port))
            except socket.error as e:
                print(f"waiting {e}") 
                time.sleep(0.2) # 5
            # else:
            #     print("breaking")
            #     break

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
                        continue
            except socket.error:
                self.socket.close()
                del self.socket
                self.connect()

Client(int(sys.argv[1]))
