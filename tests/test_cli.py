from harvest.cli import MODELS, build_parser


def test_cli_exposes_split_table_stages_and_effocr():
    parser = build_parser()

    assert parser.parse_args(["--config", "config.yaml", "detect-tables"]).command == "detect-tables"
    assert (
        parser.parse_args(["--config", "config.yaml", "extract-structure"]).command
        == "extract-structure"
    )
    assert "effocr" in MODELS
