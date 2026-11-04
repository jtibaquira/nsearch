from typing import ClassVar

import nmap
import pytest

import helpernmap


class FakeHost:
  def hostname(self):
    return "evil\x1b[31m"
  def state(self):
    return "up"
  def all_protocols(self):
    return ["tcp"]
  def __getitem__(self, proto):
    return {80: {"state": "open", "product": "\x1b]0;pwn", "version": "1", "script": {"id": "out\x1b[2J"}},
            81: {"state": "closed"}}

class FakeScanner:
  calls: ClassVar[list[tuple[str, str]]] = []
  def scan(self, hosts, arguments):
    FakeScanner.calls.append((hosts, arguments))
  def all_hosts(self):
    return ["127.0.0.1"]
  def __getitem__(self, host):
    return FakeHost()

@pytest.fixture
def scanner(monkeypatch):
  FakeScanner.calls = []
  monkeypatch.setattr(nmap, "PortScanner", FakeScanner)
  return FakeScanner

@pytest.mark.parametrize("args,message", [
  ("template:ping net:-oN/tmp/x", "Invalid target"),
  ("template:ping net:--script=x", "Invalid target"),
  ("template:../../x net:127.0.0.1", "Invalid or missing template"),
  ("template:nope net:127.0.0.1", "Invalid or missing template"),
  ("template:ping", "help run"),
  ("net:127.0.0.1", "help run"),
  ("foo", "help run"),
  ("", "help run"),
])
def test_rejected_without_scanning(scanner, capsys, args, message):
  helpernmap.HelperNmap(args).process()
  assert message in capsys.readouterr().out
  assert scanner.calls == []

@pytest.mark.parametrize("net", ["127.0.0.1", "10.0.0.0/24", "scanme.example.org", "fe80::1", "10.0.0.1-5"])
def test_valid_targets_reach_scanner(scanner, net):
  helpernmap.HelperNmap("template:ping net:" + net).process()
  assert scanner.calls == [(net, "-sn -v")]

def test_remote_output_is_sanitized(scanner, capsys):
  helpernmap.HelperNmap("template:ping net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "\x1b" not in out
  assert "port : 80" in out and "port : 81" not in out

def test_missing_nmap_is_reported(monkeypatch, capsys):
  def missing():
    raise nmap.PortScannerError("nmap program was not found in path")
  monkeypatch.setattr(nmap, "PortScanner", missing)
  helpernmap.HelperNmap("template:ping net:127.0.0.1").process()
  assert "nmap was not found" in capsys.readouterr().out

@pytest.mark.parametrize("error,message", [
  (nmap.PortScannerError("bad"), "The scan failed"),
  (KeyboardInterrupt(), "Scan interrupted"),
])
def test_scan_failures_return_to_prompt(scanner, monkeypatch, capsys, error, message):
  def fail(self, hosts, arguments):
    raise error
  monkeypatch.setattr(FakeScanner, "scan", fail)
  helpernmap.HelperNmap("template:ping net:127.0.0.1").process()
  assert message in capsys.readouterr().out
