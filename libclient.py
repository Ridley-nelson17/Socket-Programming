import sys
import selectors
import json
import io
import struct

class Message:
    def __init__(self, selector, sock, addr):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._request_queued = False
        self._jsonheader_len = None
        self.jsonheader = None
        self.response = None
        self.server_response = ""

        self.request = dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action="search", value="ring")
        )

        self._json_encode_ = lambda json_object, encoding: json.dumps(json_object, ensure_ascii=False).encode(encoding)

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r": events = selectors.EVENT_READ
        elif mode == "w": events = selectors.EVENT_WRITE
        elif mode == "rw": events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else: raise ValueError(f"Invalid events mask mode {repr(mode)}.")
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        try: data = self.sock.recv(4096) # Should be ready to read
        except BlockingIOError: pass # Resource temporarily unavailable (error no ERWOULDBLOCK)
        else:
            if data: self._recv_buffer += data
            else: raise RuntimeError("Peer closed.")

    def _write(self):
        if self._send_buffer:
            print("[INFO]: sending", repr(self._send_buffer), "to", self.addr)
            try: sent = self.sock.send(self._send_buffer) # Should be ready to write
            except BlockingIOError: pass # Resource temporarily unavailable (error no EWOULDBLOCK)
            else: self._send_buffer = self._send_buffer[sent:]
    
    def _json_decode(self, json_bytes, encoding):
        """Creates a Text IO Wrapper, then uses the text IO object to load the json object"""
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
        jsonheader_bytes = self._json_encode_(jsonheader, "utf-8")
        message_header = struct.pack(">H", len(jsonheader_bytes))
        message = message_header + jsonheader_bytes + content_bytes
        return message

    def _process_response_json_content(self):
        content = self.response
        if content.get("new_client_encoding"): print(content.get("new_client_encoding"))
        self.server_response = content.get("result")
        print(f"[INFO]: deciphered: {self.server_response}")

    def _process_response_binary_content(self):
        content = self.response
        self.server_response = content
        print(f"[INFO]: got response: {repr(content)}")
        
    def get_server_response(self):
        return self.server_response
    
    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            print("reading, mask:", mask)
            self.read()
        if mask & selectors.EVENT_WRITE:
            print("writing, mask:", mask)
            self.write()

    def read(self):
        self._read()

        if self._jsonheader_len is None: self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.response is None:
                print("[INFO] client: processing response")
                self.process_response()

    def write(self):
        if not self._request_queued: self.queue_request()

        self._write()

        if self._request_queued:
            if not self._send_buffer:
                # Set selector to listen for read events, we're done writing.
                self._set_selector_events_mask("r")

    def close(self):
        print("closing connection to", self.addr)
        try: self.selector.unregister(self.sock)
        except Exception as e: print(f"error: selector.unregister() exception for", f"{self.addr}: {repr(e)}")
        try: self.sock.close()
        except OSError as e: print(f"error: socket.close() exception for", f"{self.addr}: {repr(e)}")
        finally: self.sock = None # Delete reference to socket object for garbage collection

    def queue_request(self):
        content = self.request["content"]
        content_type = self.request["type"]
        content_encoding = self.request["encoding"]
        if content_type == "text/json":
            req = {
                "content_bytes": self._json_encode_(content, content_encoding),
                "content_type": content_type,
                "content_encoding": content_encoding,
            }
        else:
            req = {
                "content_bytes": content,
                "content_type": content_type, # binary data (application/octet-stream)
                "content_encoding": content_encoding,
            }
        message = self._create_message(**req) # Create a new message
        self._send_buffer += message
        self._request_queued = True

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

    def process_response(self):
        content_len = self.jsonheader["content-length"] # get the content length
        if not len(self._recv_buffer) >= content_len: return # return if
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        if self.jsonheader["content-type"] == "text/json":
            encoding = self.jsonheader["content-encoding"]
            self.response = self._json_decode(data, encoding)
            print("[INFO]: received:", repr(self.response), "from", self.addr)
            self._process_response_json_content()
        else:
            # Binary or unknown content-type
            self.response = data
            print(f'[INFO]: received: {self.jsonheader["content-type"]} response from', self.addr)
            self._process_response_binary_content()
        # Close when response has been processed
        # self.close()