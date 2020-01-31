import sys, socket, selectors, traceback, threading, string, time
from queue import Queue
queue = Queue()

class Server:
    def __init__(self, host, port):
        self.socket = None #socket.socket() #(socket.AF_INET, socket.SOCK_STREAM)
        self.port = port
        self.host = host
        self.buffer = 1024
        self.connections = []
        self.addresses = []

        self.decode_utf8 = lambda data: data.decode("utf-8") # function to return decoded utf-8
        self.remove_quotes = lambda string: string.replace("\"", "") # function to return string with quotes removed
        self.center = lambda string, title: f"{{:^{len(string)}}}".format(title) # function to return title centered around string
        self.send = lambda data: self.socket.send(data) # function to send encrypted data
        self.receive = lambda buffer: self.socket.recv(buffer) # function to receive and decrypt data

        # thread = threading.Thread(target=self.createSocket)
        # thread.daemon = True
        # thread.start()
    
    def refreshConnections(self):
        if len(self.connections) > 0 & len(self.addresses) > 0:
            for i, connection in enumerate(self.connections):
                try:
                    connection.send(str.encode("test"))  # test to see if connection is active
                except socket.error:
                    del self.addresses[i]
                    del self.connections[i]
                connection.close()

    def listConnections(self):
        if len(self.connections) > 0 & len(self.addresses) > 0:
            clients = ""

            for i, connection in enumerate(self.connections): clients += str(i) + 4*" " + str(self.addresses[i][0]) + 4*" " + str(self.addresses[i][1]) + 4*" " + str(self.addresses[i][2]) + "\n"
            print("clients: "+clients)
            print("\nID" + 3*" " + self.center(str(self.addresses[0][0]), "IP") + 4*" " + self.center(str(self.addresses[0][1]), "Port") + 4*" " + self.center(str(self.addresses[0][2]), "Device Name") + 4*" " + self.center(str(self.addresses[0][3]), "OS") + "\n" + clients, end="")
        else: print("No connections.")

    def createSocket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.bindSocket()
        except socket.error as e: print(f"[ERROR]: {str(e)}")
    
    def bindSocket(self):
        try:
            print("Listening on port " + str(self.port))
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            # self.acceptIncoming()
        except socket.error as e:
            print(f"[ERROR]: Error binding socket {str(e)} Retrying...")
            self.bindSocket()

    def acceptIncoming(self):
        while True:
            try:
                connection, address = self.socket.accept()
                connection.setblocking(1)
                self.connections.append(connection)
                client_info = self.decode_utf8(connection.recv(self.buffer)).split("||")
                address += client_info[0], client_info[1]
                self.addresses.append(address)
                print("\n[+] Connected to: {} {}".format(address[0], address[2]))
            except socket.error:
                print("[ERROR]: Problem accepting connections!")
                continue

    def main(self):
        while True:
            # print(self.connections, self.addresses)
            userInput = input("\n" + ">> ").lower()
            self.refreshConnections()

            if userInput == "l" or userInput == "-l": self.listConnections() 
            elif userInput == "-r": self.refreshConnections()
            else: print("\nwrong input")


    def threadHelper(self):
        while True:
            i = queue.get()
            if i == 1:
                self.createSocket()
                # self.bindSocket()
                self.acceptIncoming()
            elif i == 2:
                self.main()
            queue.task_done()
            queue.task_done()
            sys.exit(0)

    def create_threads(self):
        for _ in range(2):
            thread = threading.Thread(target=self.threadHelper)
            thread.daemon = True
            thread.start()
        queue.join()

    def create_jobs(self):
        for i in [1, 2]: queue.put(i)
        queue.join()
            

    # def selectClient(self):

s = Server("localhost", int(sys.argv[1]))
s.create_threads()
s.create_jobs()