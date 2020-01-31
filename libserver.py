import sys
import selectors
import json
import io
import struct
from threading import Thread

request_search = {
    "morpheus": "Follow the white rabbit. \U0001f430",
    "ring": "In the caves beneath the Misty Mountains. \U0001f48d",
    "\U0001f436": "\U0001f43e Playing ball! \U0001f3d0",
}

class Clients:
    def __init__(self):
        self.clients = []
    
    def get(self):
        return self.clients

    def connect(self, s):
        if s.accept(): print("[+] Connected to: " + s.address[0] + ":" + str(s.address[1]))

    def refresh(self):
        for j in range(len(self.clients)):
            self.connect(self.clients[j])

class Message:
    def __init__(self, selector, sock, addr):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False
        self.verbose_print = False

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r": events = selectors.EVENT_READ
        elif mode == "w": events = selectors.EVENT_WRITE
        elif mode == "rw": events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else: raise ValueError(f"Invalid events mask mode {repr(mode)}.")
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        try: data = self.sock.recv(4096) # Should be ready to read
        except BlockingIOError: pass # Resource temporarily unavailable (errno EWOULDBLOCK)
        else:
            if data: self._recv_buffer += data
            else: raise RuntimeError("Peer closed.")

    def _write(self):
        if self._send_buffer:
            print("[INFO]: sending", repr(self._send_buffer), "to", self.addr)
            try: sent = self.sock.send(self._send_buffer) # Should be ready to write
            except BlockingIOError: pass # Resource temporarily unavailable (errno EWOULDBLOCK)
            else:
                self._send_buffer = self._send_buffer[sent:]
                # Close when the buffer is drained. The response has been sent.
                # if sent and not self._send_buffer: self.close()

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        text_wrapper = io.TextIOWrapper(io.BytesIO(json_bytes), encoding=encoding, newline="")
        json_object = json.load(text_wrapper)
        text_wrapper.close()
        return json_object

    def _create_message(self, *, content_bytes, content_type, content_encoding):
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _create_response_json_content(self):
        action = self.request.get("action")
        if action == "search":
            query = self.request.get("value")
            answer = request_search.get(query) or f'No match for "{query}".'
            content = {"result": answer}
        else: content = {"result": f'Error: invalid action "{action}".'}
        response = {
            "content_bytes": self._json_encode(content, "utf-8"),
            "content_type": "text/json",
            "content_encoding": "utf-8",
        }
        return response

    def _create_response_binary_content(self):
        response = {
            "content_bytes": b"First 10 bytes of request: " + self.request[:10],
            "content_type": "binary/custom-server-binary-type",
            "content_encoding": "binary",
        }
        return response

    def process_events(self, mask):
        if mask & selectors.EVENT_READ: 
            if self.verbose_print: print("[INFO]: Reading")
            self.read()
        if mask & selectors.EVENT_WRITE: 
            if self.verbose_print: print("[INFO]: Writing")
            self.write()

    def read(self):
        self._read()

        if self._jsonheader_len is None: self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.request is None:
                self.process_request()

    def write(self):
        if self.request:
            if not self.response_created:
                self.create_response()

        self._write()

    def close(self):
        print("[INFO]: closing connection to", self.addr)
        try: self.selector.unregister(self.sock)
        except Exception as e: print(f"error: selector.unregister() exception for", f"{self.addr}: {repr(e)}")

        try: self.sock.close()
        except OSError as e: print(f"error: socket.close() exception for", f"{self.addr}: {repr(e)}")
        finally: self.sock = None # Delete reference to socket object for garbage collection

    def process_protoheader(self):
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._jsonheader_len = struct.unpack(">H", self._recv_buffer[:hdrlen])[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_jsonheader(self):
        hdrlen = self._jsonheader_len
        if len(self._recv_buffer) >= hdrlen:
            self.jsonheader = self._json_decode(self._recv_buffer[:hdrlen], "utf-8")
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in ("byteorder","content-length","content-type","content-encoding"):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f'Missing required header "{reqhdr}".')

    def process_request(self):
        content_length = self.jsonheader["content-length"]

        if not len(self._recv_buffer) >= content_length: return
        
        data = self._recv_buffer[:content_length]
        
        self._recv_buffer = self._recv_buffer[content_length:]
        
        if self.jsonheader["content-type"] == "text/json":
            encoding = self.jsonheader["content-encoding"]
            self.request = self._json_decode(data, encoding)
            print("[INFO]: received:", repr(self.request), "from", self.addr)
        else:
            # Binary or unknown content-type
            self.request = data
            print(f'[INFO]: received binary: {self.jsonheader["content-type"]} from', self.addr)
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")

    def create_response(self):
        if self.jsonheader["content-type"] == "text/json": response = self._create_response_json_content()
        else: response = self._create_response_binary_content() # Binary or unknown content-type
        message = self._create_message(**response)
        self.response_created = True
        self._send_buffer += message
