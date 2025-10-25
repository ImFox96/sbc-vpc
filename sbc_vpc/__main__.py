"""CLI entrypoint for the SBC to Delta DVP bridge."""

from __future__ import annotations

import argparse
import logging
import threading
from typing import TYPE_CHECKING

from .config import SerialConnectionConfig

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from .modbus import DeltaRequestLogger, ModbusSlave

try:  # pragma: no cover - serial might be optional during tests
    from serial import SerialException  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback when pyserial absent at runtime
    SerialException = OSError  # type: ignore[assignment]


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
        type=int,
        default=128,
        help="Number of registers/coils exposed by the slave",
    )
    parser.add_argument(
        "--unit-id", type=int, default=1, help="Modbus unit/slave id (1..247)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Verbosity of the runtime logger",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=8080,
        help="TCP порт для веб-интерфейса",
    )
    parser.add_argument(
        "--web-bind",
        default="0.0.0.0",
        help="Адрес привязки веб-интерфейса",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Отключить встроенный веб-интерфейс",
    )
    return parser


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not (1 <= args.unit_id <= 247):
        parser.error("--unit-id must be in 1..247")

    if not (1 <= args.data_points <= 5000):
        parser.error("--data-points must be in 1..5000")

    if not (1 <= args.web_port <= 65535):
        parser.error("--web-port must be in 1..65535")

    configure_logging(args.log_level)

    config = SerialConnectionConfig(
        port=args.port,
        baudrate=args.baudrate,
        bytesize=args.bytesize,
        parity=args.parity,
        stopbits=args.stopbits,
        timeout=args.timeout,
    )

    try:
        from .modbus import DeltaRequestLogger, ModbusSlave
    except ImportError as exc:  # pragma: no cover - optional dependency missing
        logging.getLogger(__name__).error(
            "Failed to import Modbus helpers (is pymodbus installed?): %s", exc
        )
        return 1

    request_logger = DeltaRequestLogger()
    slave = ModbusSlave(
        config=config,
        request_logger=request_logger,
        data_points=args.data_points,
        unit_id=args.unit_id,
    )

    web_server = None
    web_thread: threading.Thread | None = None
    if not args.no_web:
        try:
            from .web import WebUIServer
        except ImportError as exc:  # pragma: no cover - optional dependency missing
            logging.getLogger(__name__).error(
                "Failed to import web interface: %s", exc
            )
            return 1
        try:
            web_server = WebUIServer(
                slave=slave,
                host=args.web_bind,
                port=args.web_port,
            )
        except OSError as exc:
            logging.getLogger(__name__).error(
                "Failed to bind web interface on %s:%d: %s",
                args.web_bind,
                args.web_port,
                exc,
            )
            return 1
        web_thread = web_server.start_in_thread()

    try:
        slave.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - manual interruption
        logging.getLogger(__name__).info("Interrupted by user")
        return 0
    except (SerialException, OSError) as exc:  # type: ignore[misc]
        logging.getLogger(__name__).error(
            "Failed to open serial port %s: %s", args.port, exc
        )
        return 1
    except Exception as exc:  # pragma: no cover - startup/runtime error
        logging.getLogger(__name__).error("Failed to run Modbus slave: %s", exc)
        return 1
    finally:
        if web_server is not None:
            web_server.shutdown()
        if web_thread is not None:
            web_thread.join(timeout=1)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
