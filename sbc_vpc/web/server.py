"""Minimal HTTP server that exposes a web UI for the Modbus slave."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any, Callable

from ..modbus import ModbusSlave

_LOGGER = logging.getLogger("sbc_vpc.web")


def _load_index_template() -> bytes:
    path = resources.files(__package__) / "static" / "index.html"
    return path.read_bytes()


def _build_handler(slave: ModbusSlave) -> type[BaseHTTPRequestHandler]:
    index_bytes = _load_index_template()
    tables = slave.tables

    class WebUIRequestHandler(BaseHTTPRequestHandler):
        server_version = "SBCWebUI/0.1"
        _slave = slave
        _index = index_bytes
        _allowed_tables = tables

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - mirror BaseHTTPRequestHandler signature
            _LOGGER.info("%s - %s", self.address_string(), format % args)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path in {"/", "/index.html"}:
                self._send_bytes(self._index, "text/html; charset=utf-8")
                return
            if self.path == "/api/state":
                state = self._slave.snapshot()
                payload = {
                    "tables": {
                        name: state[name] for name in self._allowed_tables
                    },
                    "dataPoints": self._slave.data_points,
                    "unitId": self._slave.unit_id,
                }
                self._send_json(payload)
                return
            self._send_error(HTTPStatus.NOT_FOUND, "Not Found")

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path != "/api/write":
                self._send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON payload")
                return
            table = payload.get("table")
            address = payload.get("address")
            values = payload.get("values")
            if table not in self._allowed_tables:
                self._send_error(HTTPStatus.BAD_REQUEST, "Unknown table")
                return
            if not isinstance(address, int):
                self._send_error(HTTPStatus.BAD_REQUEST, "Address must be an integer")
                return
            if isinstance(values, list):
                try:
                    parsed_values = [int(v) for v in values]
                except (TypeError, ValueError):
                    self._send_error(HTTPStatus.BAD_REQUEST, "Values must be integers")
                    return
            else:
                self._send_error(HTTPStatus.BAD_REQUEST, "Values must be a list")
                return
            try:
                self._slave.write_table(table, address, parsed_values)
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            self._send_json({"status": "ok"})

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_bytes(self, payload: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_error(self, status: HTTPStatus, message: str) -> None:
            payload = {"error": message, "status": status.value}
            self._send_json(payload, status=status)

    return WebUIRequestHandler


@dataclass
class WebUIServer:
    """Wraps the HTTP server responsible for the embedded web UI."""

    slave: ModbusSlave
    host: str = "0.0.0.0"
    port: int = 8080

    def __post_init__(self) -> None:
        handler = _build_handler(self.slave)
        self._server = ThreadingHTTPServer((self.host, self.port), handler)
        address, port = self._server.server_address
        _LOGGER.info("Web UI bound to http://%s:%s", address, port)

    @property
    def server_address(self) -> tuple[str, int]:
        address, port = self._server.server_address
        return address, port

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def start_in_thread(self) -> threading.Thread:
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        return thread

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()

