# The script is a shell heredoc, not importable: pull the VS Code proxy out of it. Run: python3 tests/test_vscode_proxy.py
import os, re, socket, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

src = open(os.path.join(os.path.dirname(__file__), "..", "claude-sessions"), encoding="utf-8").read()
HOME = "/nonexistent"
exec(re.search(r"^import fcntl, select.*?(?=^def server\()", src, re.S | re.M).group(0))

# a stand-in for code serve-web: answers a request with what it got, or echoes bytes after a WebSocket upgrade
def upstream(conn):
    f = conn.makefile("rb")
    head = []
    while (ln := f.readline()) not in (b"\r\n", b""): head.append(ln.decode().strip())
    hdr = {k.lower(): v for k, v in (x.split(": ", 1) for x in head[1:])}
    if hdr.get("upgrade") == "websocket":
        conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n")
        while b := f.read1(65536): conn.sendall(b.upper())
    elif head[0].startswith("GET /vscode/?"):
        out = b'<meta id="vscode-workbench-web-configuration" data-settings="{&quot;a&quot;:1}">'
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nSet-Cookie: t=1\r\nTransfer-Encoding: chunked\r\n\r\n%x\r\n%s\r\n0\r\n\r\n" % (len(out), out))
    else:
        body = f.read(int(hdr.get("content-length", 0)))
        out = f"{head[0]}|{hdr.get('connection')}|{hdr.get('host')}|".encode() + body
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % len(out) + out)
    conn.close()

up = socket.socket(); up.bind(("127.0.0.1", 0)); up.listen()
threading.Thread(target=lambda: [threading.Thread(target=upstream, args=(up.accept()[0],), daemon=True).start() for _ in iter(int, 1)], daemon=True).start()
VSCODE["port"] = up.getsockname()[1]

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def reply(self, code, body): self.send_error(code)
    do_GET = do_POST = lambda self: vscode_proxy(self)

srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]

def raw(req, until=None):
    s = socket.create_connection(("127.0.0.1", port), 5)
    s.sendall(req)
    data = b""
    while (b := s.recv(65536)) and not (until and until in data + b): data += b
    return s, data + b

# a POST body goes through, keep-alive becomes one request per connection, and the browser's Host is kept
_, r = raw(b"POST /vscode/x?y=1 HTTP/1.1\r\nHost: 127.0.0.1:7421\r\nConnection: keep-alive\r\nContent-Length: 5\r\n\r\nhello")
assert r.startswith(b"HTTP/1.1 200 OK") and r.endswith(b"POST /vscode/x?y=1 HTTP/1.1|close|127.0.0.1:7421|hello"), r

# a WebSocket upgrade keeps its Connection header and then pipes both ways
s, r = raw(b"GET /vscode/ws HTTP/1.1\r\nHost: h\r\nConnection: Upgrade\r\nUpgrade: websocket\r\n\r\n", b"\r\n\r\n")
assert r.startswith(b"HTTP/1.1 101"), r
s.sendall(b"ping")
assert s.recv(100) == b"PING"
s.close()

# the workbench page gets a default that follows the system colour scheme; its cookie stays, chunking does not
_, r = raw(b"GET /vscode/?tkn=x HTTP/1.1\r\nHost: h\r\nAccept-Encoding: gzip\r\n\r\n")
assert b"Set-Cookie: t=1" in r and b"Transfer-Encoding" not in r, r
assert r.endswith(b'data-settings="{&quot;configurationDefaults&quot;:{&quot;window.autoDetectColorScheme&quot;:true},&quot;a&quot;:1}">'), r

# VS Code gone: a 502, not a hang
gone = socket.socket(); gone.bind(("127.0.0.1", 0)); VSCODE["port"] = gone.getsockname()[1]; gone.close()
_, r = raw(b"GET /vscode/ HTTP/1.1\r\nHost: h\r\n\r\n")
assert b" 502 " in r.split(b"\r\n")[0], r
print("ok")
