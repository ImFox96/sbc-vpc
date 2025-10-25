from __future__ import annotations

import pytest

from sbc_vpc.__main__ import build_arg_parser


def test_build_arg_parser_defaults() -> None:
    parser = build_arg_parser()
    args = parser.parse_args([])

    assert args.unit_id == 1
    assert args.data_points == 128
    assert args.json_logs is False


@pytest.mark.parametrize("value", ["0", "4097"])
def test_build_arg_parser_rejects_out_of_range_data_points(value: str) -> None:
    parser = build_arg_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--data-points", value])


@pytest.mark.parametrize("value", ["0", "248"])
def test_build_arg_parser_rejects_out_of_range_unit_id(value: str) -> None:
    parser = build_arg_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--unit-id", value])


def test_build_arg_parser_parses_json_logs_flag() -> None:
    parser = build_arg_parser()
    args = parser.parse_args(["--json-logs"])

    assert args.json_logs is True
