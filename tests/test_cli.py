import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cli  # noqa: E402


def test_dispatches_to_research_command(monkeypatch):
    calls = []
    monkeypatch.setitem(cli.COMMANDS, "research", ("dummy", lambda argv: calls.append(argv) or 0))

    exit_code = cli.main(["research", "--mode", "ranking", "--genre", "コスメ"])

    assert exit_code == 0
    assert calls == [["--mode", "ranking", "--genre", "コスメ"]]


def test_dispatches_to_track_command(monkeypatch):
    calls = []
    monkeypatch.setitem(cli.COMMANDS, "track", ("dummy", lambda argv: calls.append(argv) or 0))

    exit_code = cli.main(["track", "--csv", "report.csv"])

    assert exit_code == 0
    assert calls == [["--csv", "report.csv"]]


def test_dispatches_to_calendar_command(monkeypatch):
    calls = []
    monkeypatch.setitem(cli.COMMANDS, "calendar", ("dummy", lambda argv: calls.append(argv) or 0))

    exit_code = cli.main(["calendar", "--days", "60"])

    assert exit_code == 0
    assert calls == [["--days", "60"]]


def test_propagates_subcommand_exit_code(monkeypatch):
    monkeypatch.setitem(cli.COMMANDS, "research", ("dummy", lambda argv: 1))

    assert cli.main(["research"]) == 1


def test_unknown_command_returns_error(capsys):
    exit_code = cli.main(["nonexistent"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "不明なサブコマンド" in captured.err


def test_no_args_prints_usage_and_returns_error(capsys):
    exit_code = cli.main([])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "research" in captured.out
    assert "track" in captured.out
    assert "calendar" in captured.out


def test_help_flag_prints_usage_and_succeeds(capsys):
    exit_code = cli.main(["--help"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "サブコマンド" in captured.out
