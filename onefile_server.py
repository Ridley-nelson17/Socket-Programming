import sys, socket, selectors, traceback, threading, string

class Server:
    def __init__(self, host, port):
        self.socket = socket.socket(so)
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

        thread = threading.Thread(target=self.createSocket)
        # thread.daemon = True
        thread.start()
        # self.main()
    
    def refreshConnections(self):
        if len(self.connections) > 0:
            for i, connection in enumerate(self.connections):
                try:
                    connection.send(str.encode("test"))  # test to see if connection is active
                except socket.error:
                    del self.addresses[i]
                    del self.connections[i]
                connection.close()

    def listConnections(self):
        if len(self.connections) > 0:
            strClients = ""

            for i, connection in enumerate(self.connections):
                strClients += str(i) + 4*" " + str(self.addresses[i][0]) + 4*" " + str(self.addresses[i][1]) + 4*" " + str(self.addresses[i][2]) + "\n"

            print("\nID" + 3*" " + self.center(str(self.addresses[0][0]), "IP") + 4*" " + self.center(str(self.addresses[0][1]), "Port") + 4*" " + self.center(str(self.addresses[0][2]), "Device Name") + 4*" " + self.center(str(self.addresses[0][3]), "OS") + "\n" + strClients, end="")
        else: print("No connections.")

    def createSocket(self):
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.bindSocket()
        except socket.error as e: print(f"[ERROR]: {str(e)}")
    
    def bindSocket(self):
        try:
            print("Listening on port " + str(self.port))
            self.socket.bind((self.host, self.port))
            self.socket.listen(20)
            self.acceptIncoming()
        except socket.error as e:
            print(f"[ERROR]: Error binding socket {str(e)} Retrying...")
            self.bindSocket()

    def acceptIncoming(self):
        t = threading.Thread(target=self.main)
        t.start()
        while True:
            try:
                connection, address = self.socket.accept()
                connection.setblocking(False)
                self.connections.append(connection)
                client_info = self.decode_utf8(connection.recv(self.buffer)).split("||")
                print(client_info)
                # address += client_info[0], client_info[1], client_info[2],
                self.addresses.append(address)
                # print("\n[+] Connected to: {} {}".format(address[0], address[2]))
            except socket.error:
                print("[ERROR]: Problem accepting connections!")
                continue

    def main(self):
        while True:
            print(self.connections, self.addresses)
            userInput = input("\n" + ">> ").lower()
            self.refreshConnections()

            if userInput == "l" or userInput == "-l": self.listConnections() 
            if userInput == "-r": self.refreshConnections()
            

    # def selectClient(self):

Server("localhost", int(sys.argv[1]))