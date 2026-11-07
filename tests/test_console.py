import ctypes
import os
import subprocess
import sys

import pytest

import console
import nsearch


def test_unknown_input_is_not_executed(tmp_path, capsys):
  marker = tmp_path / "pwn"
  console.Console().onecmd(f"open({str(marker)!r}, 'w')")
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

@pytest.mark.parametrize("complete,text,expected", [
  ("complete_search", "", ["name", "category", "help", "author"]),
  ("complete_search", "a", ["author"]),
  ("complete_showfav", "", ["name", "ranking", "help"]),
  ("complete_showfav", "r", ["ranking"]),
])
def test_completion_returns_lists(complete, text, expected):
  assert getattr(console.Console(), complete)(text, "", 0, 0) == expected

def test_console_preloop_and_command_work_without_readline():
  root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  code = ("import importlib, sys\n"
    "import console\n"
    "sys.modules['readline'] = None\n"
    "console = importlib.reload(console)\n"
    "shell = console.Console()\n"
    "shell.preloop()\n"
    "assert shell.onecmd('exit')\n")
  result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, check=False)
  assert result.returncode == 0, result.stderr

def test_windows_virtual_terminal_preserves_console_mode_bits():
  class Kernel:
    mode = None
    def GetStdHandle(self, handle):
      assert handle == -11
      return "stdout"
    def GetConsoleMode(self, handle, mode):
      assert handle == "stdout"
      ctypes.cast(mode, ctypes.POINTER(ctypes.c_ulong)).contents.value = 0x0031
      return 1
    def SetConsoleMode(self, handle, mode):
      self.mode = mode
      return 1
  kernel = Kernel()
  nsearch.enableVirtualTerminal(lambda: kernel)
  assert kernel.mode == 0x0035

def test_windows_virtual_terminal_is_not_enabled_without_a_console():
  class Kernel:
    called = False
    def GetStdHandle(self, handle): return handle
    def GetConsoleMode(self, handle, mode): return 0
    def SetConsoleMode(self, handle, mode): self.called = True
  kernel = Kernel()
  nsearch.enableVirtualTerminal(lambda: kernel)
  assert not kernel.called

@pytest.mark.parametrize("failing_call", ["GetStdHandle", "GetConsoleMode", "SetConsoleMode"])
def test_windows_virtual_terminal_failures_do_not_raise(failing_call):
  class Kernel:
    def GetStdHandle(self, handle):
      if failing_call == "GetStdHandle": raise OSError("no console")
      return handle
    def GetConsoleMode(self, handle, mode):
      if failing_call == "GetConsoleMode": raise OSError("no console mode")
      ctypes.cast(mode, ctypes.POINTER(ctypes.c_ulong)).contents.value = 0
      return 1
    def SetConsoleMode(self, handle, mode):
      if failing_call == "SetConsoleMode": raise OSError("mode unavailable")
      return 1
  nsearch.enableVirtualTerminal(lambda: Kernel())

def test_windows_virtual_terminal_keeps_a_64_bit_handle():
  class Kernel:
    handle = None
    def GetStdHandle(self, handle): return 2 ** 40
    def GetConsoleMode(self, handle, mode):
      self.handle = handle
      return 0
    def SetConsoleMode(self, handle, mode): return 1
  kernel = Kernel()
  nsearch.enableVirtualTerminal(lambda: kernel)
  assert kernel.handle == 2 ** 40

def test_windows_virtual_terminal_survives_a_missing_kernel32():
  def missing():
    raise OSError("no kernel32")
  nsearch.enableVirtualTerminal(missing)

@pytest.mark.skipif(sys.platform != "win32", reason="kernel32 only exists on Windows")
def test_windows_kernel32_has_pointer_sized_handles():
  from ctypes import wintypes
  kernel32 = nsearch.windowsKernel32()
  assert kernel32.GetStdHandle.restype is wintypes.HANDLE
  assert kernel32.GetConsoleMode.argtypes[0] is wintypes.HANDLE
  nsearch.enableVirtualTerminal(nsearch.windowsKernel32)
