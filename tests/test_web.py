from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import pytest

from sbc_vpc.web import WebUIServer


class DummySlave:
    def __init__(self, data_points: int = 8, unit_id: int = 1) -> None:
        self.data_points = data_points
        self.unit_id = unit_id
        self._tables = (
            "discrete_inputs",
            "coils",
            "holding_registers",
            "input_registers",
        )
        self._state: dict[str, list[int]] = {
            name: [0] * data_points for name in self._tables
        }

    @property
    def tables(self) -> tuple[str, ...]:
        return self._tables

    def snapshot(self) -> dict[str, list[int]]:
        return {name: list(values) for name, values in self._state.items()}

    def write_table(self, table: str, address: int, values: list[int]) -> None:
        if table not in self._state:
            raise ValueError("Unknown table")
        if address < 0:
            raise ValueError("Address must be non-negative")
        if address + len(values) > len(self._state[table]):
            raise ValueError("Write exceeds configured data size")
        for offset, value in enumerate(values):
            self._state[table][address + offset] = value


@pytest.fixture()
def web_server() -> WebUIServer:
    slave = DummySlave()
    server = WebUIServer(slave=slave, host="127.0.0.1", port=0)
    thread = server.start_in_thread()
    time.sleep(0.1)
    yield server
    server.shutdown()
    thread.join(timeout=1)


def test_web_ui_state_and_write_roundtrip(web_server: WebUIServer) -> None:
    host, port = web_server.server_address

    with urllib.request.urlopen(f"http://{host}:{port}/api/state") as response:
        payload = json.load(response)

    assert payload["unitId"] == 1
    assert payload["dataPoints"] == 8
    assert set(payload["tables"].keys()) == {
        "discrete_inputs",
        "coils",
        "holding_registers",
        "input_registers",
    }

    write_request = urllib.request.Request(
        url=f"http://{host}:{port}/api/write",
        data=json.dumps(
            {"table": "holding_registers", "address": 2, "values": [42]}
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(write_request) as response:
        result = json.load(response)
    assert result == {"status": "ok"}

    with urllib.request.urlopen(f"http://{host}:{port}/api/state") as response:
        payload_after = json.load(response)
    assert payload_after["tables"]["holding_registers"][2] == 42


def test_web_ui_rejects_invalid_payload(web_server: WebUIServer) -> None:
    host, port = web_server.server_address

    bad_request = urllib.request.Request(
        url=f"http://{host}:{port}/api/write",
        data=json.dumps({"table": "unknown", "address": 0, "values": [1]}).encode(
            "utf-8"
        ),
        headers={"Content-Type": "application/json"},
    )

    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(bad_request)

    assert exc_info.value.code == 400
