import console

def test_unknown_input_is_not_executed(tmp_path, capsys):
  marker = tmp_path / "pwn"
  console.Console().onecmd("open(%r, 'w')" % str(marker))
  assert not marker.exists()
  assert "Unknown command" in capsys.readouterr().out

def test_unexpected_errors_do_not_close_console(monkeypatch, capsys):
  shell = console.Console()
  def fail(args):
    raise RuntimeError("boom")
  monkeypatch.setattr(shell, "do_search", fail)
  assert not shell.onecmd("search name:x")
  assert "boom" in capsys.readouterr().out

def test_exit_stops_the_loop():
  assert console.Console().onecmd("exit")

def test_workflow_command_reports_bad_usage(capsys):
  console.Console().onecmd("workflow nope")
  assert "help workflow" in capsys.readouterr().out
