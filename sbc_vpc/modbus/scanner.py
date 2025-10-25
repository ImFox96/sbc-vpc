"""Modbus slave utilities for logging Delta DVP requests."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Sequence

try:
    from pymodbus.datastore import (
        ModbusSequentialDataBlock,
        ModbusServerContext,
        ModbusSlaveContext,
    )
except Exception:  # pragma: no cover - version-specific import layout
    from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext  # type: ignore[attr-defined]
    try:  # pragma: no cover - pymodbus>=3.6
        from pymodbus.datastore import ModbusDeviceContext as ModbusSlaveContext  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - legacy
        from pymodbus.datastore.context import (  # type: ignore[attr-defined]
            ModbusServerContext as _ServerContext,
        )
        from pymodbus.datastore.store import (  # type: ignore[attr-defined]
            ModbusSequentialDataBlock as _SequentialBlock,
        )
        from pymodbus.datastore.context import (  # type: ignore[attr-defined]
            ModbusDeviceContext as ModbusSlaveContext,
        )

        ModbusServerContext = _ServerContext
        ModbusSequentialDataBlock = _SequentialBlock

try:
    from pymodbus.server import StartSerialServer
except Exception:  # pragma: no cover - fallback for pymodbus<3
    from pymodbus.server.sync import StartSerialServer  # type: ignore[attr-defined]

try:
    from pymodbus.device import ModbusDeviceIdentification
except Exception:  # pragma: no cover - pymodbus>=3.6 relocated
    from pymodbus.pdu.device import (  # type: ignore[attr-defined]
        ModbusDeviceIdentification,
    )
try:
    from pymodbus.transaction import ModbusRtuFramer
except Exception:  # pragma: no cover - pymodbus>=3.6 renamed
    from pymodbus.framer.rtu import FramerRTU as ModbusRtuFramer  # type: ignore[attr-defined]

from ..config import SerialConnectionConfig

_LOGGER = logging.getLogger(__name__)


class DeltaRequestLogger:
    """Helper that logs read and write operations initiated by Delta."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("sbc_vpc.delta")

    def log_read(self, table: str, address: int, count: int) -> None:
        """Log an incoming read request from Delta DVP."""

        self._logger.info(
            "Delta read %s starting at %d (len=%d)",
            table,
            address,
            count,
        )

    def log_write(self, table: str, address: int, values: Sequence[int]) -> None:
        """Log an incoming write request from Delta DVP."""

        self._logger.info(
            "Delta wrote %s starting at %d: %s",
            table,
            address,
            list(values),
        )


class LoggingDataBlock(ModbusSequentialDataBlock):
    """A data block that emits log messages on access."""

    def __init__(
        self,
        address: int,
        values: Iterable[int],
        table: str,
        request_logger: DeltaRequestLogger,
    ) -> None:
        super().__init__(address, list(values))
        self._table = table
        self._request_logger = request_logger

    def getValues(self, address: int, count: int = 1) -> list[int]:  # noqa: N802
        self._request_logger.log_read(self._table, address, count)
        return super().getValues(address, count)

    def setValues(  # noqa: N802
        self, address: int, values: Sequence[int] | int
    ) -> None:
        data = list(values) if isinstance(values, Sequence) else [int(values)]
        self._request_logger.log_write(self._table, address, data)
        super().setValues(address, data)


@dataclass(slots=True)
class ModbusSlave:
    """Serial Modbus slave ready to talk with Delta DVP."""

    config: SerialConnectionConfig
    request_logger: DeltaRequestLogger
    data_points: int = 128
    unit_id: int = 1

    def __post_init__(self) -> None:
        self._context = self._build_context()
        self._identity = self._build_identity()

    def _build_context(self) -> ModbusServerContext:
        block = lambda table: LoggingDataBlock(  # noqa: E731
            address=0,
            values=[0] * self.data_points,
            table=table,
            request_logger=self.request_logger,
        )
        slave_context = ModbusSlaveContext(
            di=block("discrete_inputs"),
            co=block("coils"),
            hr=block("holding_registers"),
            ir=block("input_registers"),
        )
        return ModbusServerContext(slaves={self.unit_id: slave_context}, single=False)

    def _build_identity(self) -> ModbusDeviceIdentification:
        identity = ModbusDeviceIdentification()
        identity.VendorName = "SBC Delta Bridge"  # type: ignore[attr-defined]
        identity.ProductCode = "SBC"  # type: ignore[attr-defined]
        identity.VendorUrl = "https://example.com/sbc-delta"
        identity.ProductName = "Orange Pi Modbus Slave"
        identity.ModelName = "sbc-vpc"
        identity.MajorMinorRevision = "0.1"
        return identity

    def serve_forever(self) -> None:
        """Start the Modbus RTU slave loop."""

        _LOGGER.info("Starting Modbus slave on %s", self.config.port)
        StartSerialServer(  # pragma: no cover - integration behaviour
            context=self._context,
            identity=self._identity,
            framer=ModbusRtuFramer,
            **self.config.as_dict(),
        )
