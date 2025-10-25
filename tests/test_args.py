from __future__ import annotations

import pytest

from sbc_vpc.__main__ import build_arg_parser, main
from sbc_vpc.config import SerialConnectionConfig


def test_arg_parser_unit_id_default_and_override() -> None:
    parser = build_arg_parser()
    ns = parser.parse_args([])
    assert ns.unit_id == 1

    ns2 = parser.parse_args(["--unit-id", "77"])
    assert ns2.unit_id == 77


def test_serial_config_as_dict() -> None:
    cfg = SerialConnectionConfig(
        port="/dev/ttyUSB9",
        baudrate=19200,
        bytesize=7,
        parity="E",
        stopbits=1,
        timeout=2.5,
    )
    params = cfg.as_dict()
    assert params["port"] == "/dev/ttyUSB9"
    assert params["baudrate"] == 19200
    assert params["bytesize"] == 7
    assert params["parity"] == "E"
    assert params["stopbits"] == 1
    assert params["timeout"] == 2.5


def test_main_rejects_out_of_range_data_points() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--data-points", "0"])
    assert exc_info.value.code == 2

    with pytest.raises(SystemExit) as exc_info_high:
        main(["--data-points", "6000"])
    assert exc_info_high.value.code == 2
