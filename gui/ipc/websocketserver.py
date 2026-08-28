# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import base64
import hashlib
from http import HTTPStatus
import mimetypes
import os
import struct
import urllib.parse

from PyQt6.QtNetwork import QHostAddress, QTcpServer

from .socketinterface import SocketInterface
from ...conf import DEBUG_MODE
from ...utils.logging import logger

# RFC 6455 — The WebSocket Protocol
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA


class Connection:

    def __init__(self, sock):
        self.sock = sock
        self.buffer = bytearray()       # unparsed bytes received from socket
        self.isWebSocket = False
        self.fragments = bytearray()    # a buffer for combining payloads of fragmented WebSocket messages
        self.fragmentsOpcode = None


class WebSocketServer(SocketInterface):
    """A minimal HTTP + WebSocket server"""

    def __init__(self, parent, rootDir, port=0):
        SocketInterface.__init__(self, parent)

        self.rootDir = os.path.realpath(rootDir)

        self._connections = {}

        self.server = QTcpServer(parent)
        self.server.newConnection.connect(self._onNewConnection)

        if not self.server.listen(QHostAddress.SpecialAddress.LocalHost, port):
            logger.error(f"Failed to start HTTP/WebSocket server: {self.server.errorString()}")
            return

        logger.debug(f"HTTP/WebSocket server is listening on 127.0.0.1:{self.port()}.")

    def port(self):
        return self.server.serverPort()

    def url(self, path="/"):
        return f"http://127.0.0.1:{self.port()}{path}"

    def teardown(self):
        for sock in list(self._connections):
            sock.readyRead.disconnect()
            sock.disconnected.disconnect()
            sock.close()
        self._connections.clear()

        self.server.close()

    def closeActiveWebSocket(self):
        if not self.sock:
            return

        conn = self._connections.get(self.sock)
        if conn and conn.isWebSocket:
            self._sendFrame(self.sock, b"", OPCODE_CLOSE)

        self.sock.disconnectFromHost()

    def writeToSocket(self, data):
        if self.sock:
            self._sendFrame(self.sock, data, OPCODE_TEXT)

    def _onNewConnection(self):
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            if not sock:
                continue

            self._connections[sock] = Connection(sock)
            sock.readyRead.connect(lambda s=sock: self._onReadyRead(s))
            sock.disconnected.connect(lambda s=sock: self._onSockDisconnected(s))

    def _onSockDisconnected(self, sock):
        conn = self._connections.pop(sock, None)

        if conn and conn.isWebSocket and sock is self.sock:
            self.sock = None
            logger.debug("Preview browser disconnected.")
            self.disconnected.emit()

        sock.deleteLater()

    def _onReadyRead(self, sock):
        conn = self._connections.get(sock)
        if not conn:
            return

        conn.buffer += bytes(sock.readAll())

        if conn.isWebSocket:
            self._processWebSocketFrames(sock, conn)
        else:
            self._processHttpRequest(sock, conn)

    def _processHttpRequest(self, sock, conn):
        header_end = conn.buffer.find(b"\r\n\r\n")
        if header_end == -1:
            return

        header_bytes = bytes(conn.buffer[:header_end])
        del conn.buffer[:header_end + 4]

        try:
            lines = header_bytes.decode("iso-8859-1").split("\r\n")
            request_line = lines[0]
            method, path, _ = request_line.split(" ", 2)

            if DEBUG_MODE:
                logger.debug("HTTP REQ: " + request_line)

            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, _, value = line.partition(":")
                    headers[key.strip().lower()] = value.strip()

        except Exception:
            self._writeHttpResponse(sock, 400, b"Bad Request")
            sock.disconnectFromHost()
            return

        if headers.get("upgrade", "").lower() == "websocket" and "sec-websocket-key" in headers:
            self._doWebSocketHandshake(sock, conn, headers)
            return

        if method not in ("GET", "HEAD"):
            self._writeHttpResponse(sock, 405, b"Method Not Allowed")
            sock.disconnectFromHost()
            return

        self._serveStaticFile(sock, path, head=(method == "HEAD"))

    def _serveStaticFile(self, sock, path, head=False):
        url_path = urllib.parse.urlsplit(path).path
        url_path = urllib.parse.unquote(url_path)

        rel_path = url_path.lstrip("/")
        abs_path = os.path.realpath(os.path.join(self.rootDir, rel_path))

        # prevent path traversal outside of the web root directory
        if os.path.commonpath([abs_path, self.rootDir]) != self.rootDir or not os.path.isfile(abs_path):
            self._writeHttpResponse(sock, 404, b"Not Found")
            sock.disconnectFromHost()
            return

        content_type = mimetypes.guess_type(abs_path)[0] or "application/octet-stream"

        try:
            with open(abs_path, "rb") as f:
                data = f.read()
        except OSError as e:
            logger.error(f"Failed to read {abs_path}: {e}")
            self._writeHttpResponse(sock, 500, b"Internal Server Error")
            sock.disconnectFromHost()
            return

        self._writeHttpResponse(sock, 200, b"" if head else data, content_type, content_length=len(data))
        sock.disconnectFromHost()

    def _writeHttpResponse(self, sock, status, body, content_type="text/plain", content_length=None):
        status = HTTPStatus(status)

        if content_length is None:
            content_length = len(body)

        header = (
            f"HTTP/1.1 {status} {status.phrase}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {content_length}\r\n"
            f"Connection: close\r\n"
            f"Cache-Control: no-store\r\n"
            f"\r\n"
        ).encode("ascii")

        sock.write(header + body)

    def _doWebSocketHandshake(self, sock, conn, headers):
        key = headers["sec-websocket-key"]
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode("ascii")).digest()).decode("ascii")     # nosec B324 - required by the WebSocket protocol (RFC 6455)

        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        ).encode("ascii")
        sock.write(response)

        conn.isWebSocket = True

        # only one WebSocket connection is supported at a time
        if self.sock and self.sock in self._connections:
            del self._connections[self.sock]
            self.sock.disconnectFromHost()

        self.sock = sock

        logger.debug("Preview browser connected.")
        self.connected.emit()

    def _processWebSocketFrames(self, sock, conn):
        while True:
            frame = self._tryParseFrame(conn.buffer)
            if frame is None:
                return

            fin, opcode, payload, consumed = frame
            del conn.buffer[:consumed]

            if opcode == OPCODE_CLOSE:
                sock.disconnectFromHost()
                return

            if opcode == OPCODE_PING:
                self._sendFrame(sock, payload, OPCODE_PONG)
                continue

            if opcode == OPCODE_PONG:
                continue

            if opcode == OPCODE_CONTINUATION:
                conn.fragments += payload
                if fin:
                    self._onWebSocketMessage(conn.fragmentsOpcode, bytes(conn.fragments))
                    conn.fragments = bytearray()
                    conn.fragmentsOpcode = None
                continue

            if not fin:
                conn.fragmentsOpcode = opcode
                conn.fragments = bytearray(payload)
                continue

            self._onWebSocketMessage(opcode, payload)

    def _onWebSocketMessage(self, opcode, payload):
        if opcode != OPCODE_TEXT:
            return

        self.processJsonData(payload)

    @staticmethod
    def _tryParseFrame(buf):
        if len(buf) < 2:
            return None

        b0, b1 = buf[0], buf[1]
        fin = bool(b0 & 0x80)
        opcode = b0 & 0x0F
        masked = bool(b1 & 0x80)
        length = b1 & 0x7F

        offset = 2
        if length == 126:
            if len(buf) < offset + 2:
                return None
            length = struct.unpack(">H", buf[offset:offset + 2])[0]     # 16-bit uint
            offset += 2
        elif length == 127:
            if len(buf) < offset + 8:
                return None
            length = struct.unpack(">Q", buf[offset:offset + 8])[0]     # 64-bit uint
            offset += 8

        if masked:
            if len(buf) < offset + 4:
                return None
            mask = buf[offset:offset + 4]
            offset += 4
        else:
            mask = None

        if len(buf) < offset + length:
            return None

        payload = bytearray(buf[offset:offset + length])
        if mask:
            for i in range(len(payload)):
                payload[i] ^= mask[i % 4]       # XOR

        return fin, opcode, bytes(payload), offset + length

    def _sendFrame(self, sock, data: bytes, opcode: int):
        header = bytearray()
        header.append(0x80 | opcode)    # FIN=1

        length = len(data)
        if length < 126:
            header.append(length)
        elif length < 0x10000:
            header.append(126)
            header += struct.pack(">H", length)
        else:
            header.append(127)
            header += struct.pack(">Q", length)

        sock.write(bytes(header) + data)
