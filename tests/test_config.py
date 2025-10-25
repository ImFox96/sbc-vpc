from __future__ import annotations

from sbc_vpc.config import SerialConnectionConfig


def test_serial_connection_config_as_dict() -> None:
    config = SerialConnectionConfig(
        port="/dev/ttyUSB1",
        baudrate=19200,
        bytesize=7,
        parity="E",
        stopbits=2,
        timeout=0.5,
    )

    assert config.as_dict() == {
        "port": "/dev/ttyUSB1",
        "baudrate": 19200,
        "bytesize": 7,
        "parity": "E",
        "stopbits": 2,
        "timeout": 0.5,
    }
