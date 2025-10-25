"""CLI entrypoint for the SBC to Delta DVP bridge."""

from __future__ import annotations

import argparse
import logging

from .config import SerialConnectionConfig
from .modbus import DeltaRequestLogger, ModbusSlave


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

    configure_logging(args.log_level)

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
    except KeyboardInterrupt:  # pragma: no cover - manual interruption
        logging.getLogger(__name__).info("Interrupted by user")
        return 0
    except Exception as exc:  # pragma: no cover - startup/runtime error
        logging.getLogger(__name__).error("Failed to run Modbus slave: %s", exc)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
