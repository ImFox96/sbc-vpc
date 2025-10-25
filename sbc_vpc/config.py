"""Configuration helpers for the SBC to Delta DVP bridge."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SerialConnectionConfig:
    """Configuration parameters for the USB/serial Modbus connection."""

    port: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"
    stopbits: int = 1
    timeout: float = 1.0

    def as_dict(self) -> dict[str, object]:
        """Return a mapping compatible with :mod:`pymodbus` configuration."""

        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity,
            "stopbits": self.stopbits,
            "timeout": self.timeout,
        }
