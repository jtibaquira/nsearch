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

def test_workflow_resume_is_in_help_and_completion(capsys):
  shell = console.Console()
  assert shell.complete_workflow("res", "workflow res", 9, 12) == ["resume"]
  shell.onecmd("help workflow")
  assert "workflow resume id:1" in capsys.readouterr().out

def test_workflow_report_and_compare_are_in_help_and_completion(capsys):
  shell = console.Console()
  assert shell.complete_workflow("rep", "workflow rep", 9, 12) == ["report"]
  assert shell.complete_workflow("su", "workflow su", 9, 11) == ["suggest"]
  assert shell.complete_workflow("co", "workflow co", 9, 11) == ["compare"]
  shell.onecmd("help workflow")
  out = capsys.readouterr().out
  assert "workflow report id:1 format:json" in out and "workflow compare id:1 with:2" in out and "workflow suggest id:1" in out
