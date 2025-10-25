from __future__ import annotations

import pytest

pytest.importorskip("pymodbus")

from sbc_vpc.modbus.scanner import DeltaRequestLogger, LoggingDataBlock


class _Recorder(DeltaRequestLogger):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[tuple[str, str, int, int | list[int]]] = []

    def log_read(self, table: str, address: int, count: int) -> None:  # type: ignore[override]
        self.events.append(("read", table, address, count))

    def log_write(self, table: str, address: int, values):  # type: ignore[override]
        self.events.append(("write", table, address, list(values)))


def test_logging_data_block_records_reads_and_writes() -> None:
    recorder = _Recorder()
    block = LoggingDataBlock(0, [0] * 4, "holding_registers", recorder)

    block.setValues(1, [10, 11])
    assert block.getValues(1, 2) == [10, 11]

    assert recorder.events == [
        ("write", "holding_registers", 1, [10, 11]),
        ("read", "holding_registers", 1, 2),
    ]
