"""CLI entrypoint for the SBC to Delta DVP bridge."""

from __future__ import annotations

import argparse
import json
import logging
from typing import Callable

from .config import SerialConnectionConfig
from .modbus import DeltaRequestLogger, ModbusSlave


try:  # pragma: no cover - optional dependency for better error messages
    from serial import SerialException  # type: ignore
except Exception:  # pragma: no cover - pyserial not installed during tests
    SerialException = OSError  # type: ignore[misc, assignment]


def _bounded_int(min_value: int, max_value: int) -> Callable[[str], int]:
    def _convert(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:  # pragma: no cover - argparse handles messaging
            raise argparse.ArgumentTypeError(str(exc)) from exc
        if not min_value <= parsed <= max_value:
            raise argparse.ArgumentTypeError(
                f"Value must be between {min_value} and {max_value}"
            )
        return parsed

    return _convert


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Orange Pi Modbus slave to observe Delta DVP traffic.",
    )
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port name")
    parser.add_argument("--baudrate", type=int, default=9600, help="Serial baudrate")
    parser.add_argument(
        "--bytesize", type=int, default=8, choices=(5, 6, 7, 8), help="Data bits"
    )
    parser.add_argument(
        "--parity", default="N", choices=("N", "E", "O", "M", "S"), help="Parity"
    )
    parser.add_argument(
        "--stopbits", type=int, default=1, choices=(1, 2), help="Stop bits"
    )
    parser.add_argument(
        "--timeout", type=float, default=1.0, help="Serial read timeout in seconds"
    )
    parser.add_argument(
        "--data-points",
        type=_bounded_int(1, 4096),
        default=128,
        help="Number of registers/coils exposed by the slave",
    )
    parser.add_argument(
        "--unit-id",
        type=_bounded_int(1, 247),
        default=1,
        help="Modbus unit identifier of the DVP controller",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Verbosity of the runtime logger",
    )
    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Emit logs in JSON format for easier ingestion",
    )
    return parser


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter to improve log collection."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str, *, json_logs: bool) -> None:
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler()
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    logger.addHandler(handler)


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    configure_logging(args.log_level, json_logs=args.json_logs)

    config = SerialConnectionConfig(
        port=args.port,
        baudrate=args.baudrate,
        bytesize=args.bytesize,
        parity=args.parity,
        stopbits=args.stopbits,
        timeout=args.timeout,
    )

    request_logger = DeltaRequestLogger()
    slave = ModbusSlave(
        config=config,
        request_logger=request_logger,
        data_points=args.data_points,
        unit_id=args.unit_id,
    )
    try:
        slave.serve_forever()
    except (SerialException, OSError) as exc:
        logging.getLogger(__name__).error(
            "Failed to open serial port %s: %s", args.port, exc
        )
        return 1
    except KeyboardInterrupt:  # pragma: no cover - manual interruption
        logging.getLogger(__name__).info("Interrupted by user")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
