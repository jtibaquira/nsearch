import ntpath
import os
import re
import shlex
from typing import ClassVar

import nmap
import pytest
import yaml

import dbmodule
import helpernmap
from scriptpolicy import analyzeScriptExpression


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
  def __init__(self, nmap_search_path=None):
    pass

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
  def missing(**kwargs):
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

def test_scan_output_is_exact(scanner, capsys):
  helpernmap.HelperNmap("net:127.0.0.1 template:ping").process()
  lines = capsys.readouterr().out.splitlines()
  start = lines.index("----------------------------------------------------")
  assert lines[start + 1:] == [
    "Host : 127.0.0.1 (evil?[31m)",
    "State : up",
    "----------",
    "Protocol : tcp",
    "port : 80\tstate : open ?]0;pwn 1 ",
    "id => out?[2J",
  ]

def test_windows_runs_the_configured_nmap_then_the_install_folders(monkeypatch):
  def fakeScanner(**kwargs):
    fakeScanner.kwargs = kwargs
    return FakeScanner()
  monkeypatch.setattr(helpernmap.sys, "platform", "win32")
  monkeypatch.setattr(helpernmap.dbmodule, "scriptsPath", r"C:\Nmap\scripts" + "\\")
  monkeypatch.setattr(nmap, "PortScanner", fakeScanner)
  helpernmap.newScanner()
  assert fakeScanner.kwargs == {"nmap_search_path": (
    r"C:\Nmap\nmap.exe", r"C:\Program Files (x86)\Nmap\nmap.exe", r"C:\Program Files\Nmap\nmap.exe")}

def test_windows_never_runs_nmap_from_path_or_the_current_folder(monkeypatch, tmp_path):
  def fakeScanner(**kwargs):
    fakeScanner.kwargs = kwargs
    return FakeScanner()
  monkeypatch.setattr(helpernmap.sys, "platform", "win32")
  monkeypatch.setattr(helpernmap.dbmodule, "scriptsPath", str(tmp_path / "scripts"))
  monkeypatch.setattr(nmap, "PortScanner", fakeScanner)
  helpernmap.newScanner()
  # A bare name is what Windows would look up in the current folder and in PATH
  assert not {"nmap", "nmap.exe"} & set(fakeScanner.kwargs["nmap_search_path"])

@pytest.mark.parametrize("scriptsPath", ["", "scripts", r".\scripts", r"\scripts"])
def test_windows_ignores_empty_or_relative_scripts_path(monkeypatch, scriptsPath):
  def fakeScanner(**kwargs):
    fakeScanner.kwargs = kwargs
    return FakeScanner()
  monkeypatch.setattr(helpernmap.sys, "platform", "win32")
  monkeypatch.setattr(helpernmap.dbmodule, "scriptsPath", scriptsPath)
  monkeypatch.setattr(nmap, "PortScanner", fakeScanner)
  helpernmap.newScanner()
  assert fakeScanner.kwargs == {"nmap_search_path": helpernmap.WINDOWS_NMAP}
  assert all(ntpath.splitdrive(path)[0] and ntpath.isabs(path) for path in fakeScanner.kwargs["nmap_search_path"])

@pytest.mark.parametrize("scriptsPath,expected", [
  (r"D:\Tools\Nmap\scripts", r"D:\Tools\Nmap\nmap.exe"),
  (r"\\server\share\Nmap\scripts", r"\\server\share\Nmap\nmap.exe"),
])
def test_windows_puts_configured_nmap_first_when_scripts_path_is_absolute(monkeypatch, scriptsPath, expected):
  def fakeScanner(**kwargs):
    fakeScanner.kwargs = kwargs
    return FakeScanner()
  monkeypatch.setattr(helpernmap.sys, "platform", "win32")
  monkeypatch.setattr(helpernmap.dbmodule, "scriptsPath", scriptsPath)
  monkeypatch.setattr(nmap, "PortScanner", fakeScanner)
  helpernmap.newScanner()
  assert fakeScanner.kwargs == {"nmap_search_path": (expected,) + helpernmap.WINDOWS_NMAP}
  assert all(ntpath.splitdrive(path)[0] and ntpath.isabs(path) for path in fakeScanner.kwargs["nmap_search_path"])

def test_other_systems_keep_the_default_nmap_lookup(monkeypatch):
  def fakeScanner(**kwargs):
    fakeScanner.kwargs = kwargs
    return FakeScanner()
  monkeypatch.setattr(helpernmap.sys, "platform", "linux")
  monkeypatch.setattr(nmap, "PortScanner", fakeScanner)
  helpernmap.newScanner()
  assert fakeScanner.kwargs == {}

def test_missing_nmap_is_reported_on_windows(monkeypatch, capsys):
  def missing(**kwargs):
    raise nmap.PortScannerError("nmap program was not found in path")
  monkeypatch.setattr(helpernmap.sys, "platform", "win32")
  monkeypatch.setattr(nmap, "PortScanner", missing)
  helpernmap.HelperNmap("template:ping net:127.0.0.1").process()
  assert "nmap was not found" in capsys.readouterr().out

SCRIPTS = {
  "http-title": {"default", "safe"},
  "ssh2-enum-algos": {"discovery", "safe"},
  "http-sql": {"intrusive", "vuln"},
  "http-slowloris": {"dos", "intrusive"},
  "bc": {"broadcast", "safe"},
  "http-virustotal": {"external", "safe"},
}

@pytest.fixture
def templates(tmp_path, monkeypatch):
  monkeypatch.setattr(helpernmap, "BASE_DIR", str(tmp_path))
  monkeypatch.setattr(dbmodule, "scriptCategories", lambda: SCRIPTS)
  folder = tmp_path / "templates"
  folder.mkdir()
  def write(name, arguments):
    (folder / (name + ".yaml")).write_text(yaml.safe_dump({name: {"arguments": arguments}}), encoding="utf-8")
  return write

def repoScriptDb():
  path = os.path.join(dbmodule.BASE_DIR, "script.db")
  with open(path, encoding="utf-8") as f:
    return {name: set(re.findall(r'"([a-z]+)"', categories))
      for name, categories in re.findall(r'filename = "([^"]+)\.nse", categories = \{([^}]*)\}', f.read())}

def test_safe_script_selector_scans_without_asking(scanner, templates, monkeypatch):
  templates("safeonly", "-sV -p 80 --script http-title")
  def forbidden(prompt):
    raise AssertionError("should not ask")
  monkeypatch.setattr("builtins.input", forbidden)
  helpernmap.HelperNmap("template:safeonly net:127.0.0.1").process()
  assert scanner.calls == [("127.0.0.1", "-sV -p 80 --script http-title")]

def test_shipped_ssh_template_scans_without_asking(scanner, monkeypatch):
  monkeypatch.setattr(dbmodule, "scriptCategories", repoScriptDb)
  def forbidden(prompt):
    raise AssertionError("should not ask")
  monkeypatch.setattr("builtins.input", forbidden)
  helpernmap.HelperNmap("template:ssh net:127.0.0.1").process()
  assert scanner.calls == [("127.0.0.1", "-sV -p ssh --script ssh2-enum-algos")]

@pytest.mark.parametrize("reply", ["n", "", EOFError, KeyboardInterrupt])
def test_unsafe_script_selector_asks_and_does_not_create_scanner_when_declined(templates, monkeypatch, capsys, reply):
  templates("risky", "-sV -p 80 --script http-sql")
  def failScanner():
    raise AssertionError("PortScanner should not be created")
  monkeypatch.setattr(nmap, "PortScanner", failScanner)
  asked = []
  def respond(prompt):
    asked.append(prompt)
    if isinstance(reply, str):
      return reply
    raise reply
  monkeypatch.setattr("builtins.input", respond)
  helpernmap.HelperNmap("template:risky net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "Template scan for target: 127.0.0.1" in out
  assert "-sV -p 80 --script http-sql" in out
  assert "selects scripts outside the safe category" in out
  assert "Scan cancelled" in out
  assert len(asked) == 1

def test_unsafe_script_selector_scans_when_confirmed(scanner, templates, monkeypatch, capsys):
  templates("risky", "-sV -p 80 --script http-sql")
  monkeypatch.setattr("builtins.input", lambda prompt: "y")
  helpernmap.HelperNmap("template:risky net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "Template scan for target: 127.0.0.1" in out
  assert scanner.calls == [("127.0.0.1", "-sV -p 80 --script http-sql")]

def test_unparseable_script_selector_asks_and_keeps_original_arguments(scanner, templates, monkeypatch, capsys):
  raw = "-sV --script custom-local-script -oX -"
  templates("custom", raw)
  monkeypatch.setattr("builtins.input", lambda prompt: "y")
  helpernmap.HelperNmap("template:custom net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "uses a script selector that could not be verified" in out
  assert scanner.calls == [("127.0.0.1", raw)]

def test_shlex_failure_asks_and_does_not_create_scanner_when_declined(templates, monkeypatch, capsys):
  templates("unclosed", "-sV --script 'http-title")
  def failScanner():
    raise AssertionError("PortScanner should not be created")
  monkeypatch.setattr(nmap, "PortScanner", failScanner)
  asked = []
  monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "n")
  helpernmap.HelperNmap("template:unclosed net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "uses a script selector that could not be verified" in out
  assert "Scan cancelled" in out
  assert len(asked) == 1

def test_unreadable_script_db_asks_and_does_not_create_scanner_when_declined(templates, monkeypatch, capsys):
  templates("safeonly", "-sV -p 80 --script http-title")
  def failCategories():
    raise OSError("cannot read script.db")
  def failScanner():
    raise AssertionError("PortScanner should not be created")
  monkeypatch.setattr(dbmodule, "scriptCategories", failCategories)
  monkeypatch.setattr(nmap, "PortScanner", failScanner)
  asked = []
  monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "n")
  helpernmap.HelperNmap("template:safeonly net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "uses a script selector that could not be verified" in out
  assert "Scan cancelled" in out
  assert len(asked) == 1

def test_external_safe_script_explicitly_warns_about_third_parties(scanner, templates, monkeypatch, capsys):
  templates("ext", "-sV -p 80 --script http-virustotal")
  monkeypatch.setattr("builtins.input", lambda prompt: "n")
  helpernmap.HelperNmap("template:ext net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "Reason: selects external scripts that may contact third-party services\n" in out
  assert "outside the safe category" not in out
  assert "intrusive" not in out.lower()
  assert scanner.calls == []

@pytest.mark.parametrize("expression", [
  "dos", "broadcast", "http-slowloris", "http-title or dos", "bc", "http-*", "not dos", "not broadcast",
  "DOS", "Broadcast", "not DOS", "not Broadcast", "safe and not Dos", "SAFE AND NOT DOS",
  "ALL", "TRUE", "not FALSE", "http-title OR DOS",
  "dos and safe", "DOS and safe", "dos and not dos",
  "FALSE OR DOS", "HTTP-SLOWLORIS", "http-slowloris.NSE", "./http-slowloris.nse",
  "/opt/nmap/scripts/http-slowloris.nse", r"C:\Nmap\scripts\http-slowloris.nse",
  r"..\scripts\HTTP-SLOWLORIS.NSE",
])
def test_dos_and_broadcast_are_rejected_before_creating_scanner(templates, monkeypatch, capsys, expression):
  templates("bad", f"-sV --script '{expression}'")
  def failScanner():
    raise AssertionError("PortScanner should not be created")
  def failInput(prompt):
    raise AssertionError("should not ask for confirmation")
  monkeypatch.setattr(nmap, "PortScanner", failScanner)
  monkeypatch.setattr("builtins.input", failInput)
  helpernmap.HelperNmap("template:bad net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "This template uses scripts in the dos or broadcast categories, which are not allowed" in out

@pytest.mark.parametrize("expression", ["./scripts/", "/opt/nmap/scripts", r"C:\Nmap\scripts", "./scripts/ or DOS", "DOS or ./scripts/", "./http-slowloris", r"C:\Nmap\scripts\http-slowloris"])
def test_script_folders_are_rejected_with_their_own_message(templates, monkeypatch, capsys, expression):
  templates("bad", f"-sV --script '{expression}'")
  def failScanner():
    raise AssertionError("PortScanner should not be created")
  def failInput(prompt):
    raise AssertionError("should not ask for confirmation")
  monkeypatch.setattr(nmap, "PortScanner", failScanner)
  monkeypatch.setattr("builtins.input", failInput)
  helpernmap.HelperNmap("template:bad net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "This template uses a script folder or a script path without .nse, which is not allowed. Name the scripts or categories instead, or add .nse to the path" in out
  assert "dos or broadcast categories" not in out

def test_a_safe_script_by_path_still_asks_and_does_not_scan_when_declined(templates, monkeypatch, capsys):
  templates("bypath", "-sV --script ./http-title.nse")
  def failScanner():
    raise AssertionError("PortScanner should not be created")
  asked = []
  def answerNo(prompt):
    asked.append(prompt)
    return "n"
  monkeypatch.setattr(nmap, "PortScanner", failScanner)
  monkeypatch.setattr("builtins.input", answerNo)
  helpernmap.HelperNmap("template:bypath net:127.0.0.1").process()
  assert len(asked) == 1

@pytest.mark.parametrize("expression", [
  "http-*", "not dos", "not broadcast", "DOS", "Broadcast", "not DOS", "safe and not Dos", "SAFE AND NOT DOS", "ALL", "TRUE",
  "dos and safe", "DOS and safe", "dos and not dos",
])
def test_mixed_and_negated_selectors_with_blocked_results_are_rejected_against_real_script_db(templates, monkeypatch, capsys, expression):
  templates("bad", f"-sV --script '{expression}'")
  monkeypatch.setattr(dbmodule, "scriptCategories", repoScriptDb)
  def failScanner():
    raise AssertionError("PortScanner should not be created")
  def failInput(prompt):
    raise AssertionError("should not ask for confirmation")
  monkeypatch.setattr(nmap, "PortScanner", failScanner)
  monkeypatch.setattr("builtins.input", failInput)
  helpernmap.HelperNmap("template:bad net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "This template uses scripts in the dos or broadcast categories, which are not allowed" in out

@pytest.mark.parametrize("expression", [
  "http-title OR ssh2-enum-algos",
  "(http-title OR http-sql) AND SAFE",
  "FALSE",
  "http-title OR FALSE",
  "http-title.nse",
])
def test_uppercase_operators_categories_and_false_in_safe_templates_scan_without_asking(scanner, templates, monkeypatch, expression):
  arguments = f"-sV -p 80 --script '{expression}'"
  templates("safeexpr", arguments)
  def failInput(prompt):
    raise AssertionError("should not ask for confirmation")
  monkeypatch.setattr("builtins.input", failInput)
  helpernmap.HelperNmap("template:safeexpr net:127.0.0.1").process()
  assert scanner.calls == [("127.0.0.1", arguments)]

@pytest.mark.parametrize("expression", ["HTTP-Title", "HTTP-*", "http-title.NSE"])
def test_script_names_wildcards_and_nse_suffix_remain_case_sensitive(templates, monkeypatch, capsys, expression):
  templates("cased", f"-sV -p 80 --script '{expression}'")
  def failScanner():
    raise AssertionError("PortScanner should not be created")
  monkeypatch.setattr(nmap, "PortScanner", failScanner)
  asked = []
  monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "n")
  helpernmap.HelperNmap("template:cased net:127.0.0.1").process()
  out = capsys.readouterr().out
  assert "uses a script selector that could not be verified" in out
  assert "Scan cancelled" in out
  assert len(asked) == 1

@pytest.mark.parametrize("arguments,needsConfirm,blocked", [
  ("-sV --script http-title", False, False),
  ("-sV --script=http-title", False, False),
  ("-sV --script http-title --script=ssh2-enum-algos", False, False),
  ("-sV --script http-title --script=http-sql", True, False),
  ("-sV --script=http-sql --script http-title", True, False),
  ("-sV --script=http-title --script dos", False, True),
])
def test_script_option_forms_and_repeated_flags_are_detected(scanner, templates, monkeypatch, capsys, arguments, needsConfirm, blocked):
  templates("multi", arguments)
  asked = []
  monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "y")
  helpernmap.HelperNmap("template:multi net:127.0.0.1").process()
  out = capsys.readouterr().out
  if blocked:
    assert "not allowed" in out
    assert asked == []
    assert scanner.calls == []
  elif needsConfirm:
    assert len(asked) == 1
    assert scanner.calls == [("127.0.0.1", arguments)]
  else:
    assert asked == []
    assert scanner.calls == [("127.0.0.1", arguments)]

def test_shipped_http_template_excludes_dangerous_categories_against_real_script_db(scanner, monkeypatch, capsys):
  realScripts = repoScriptDb()
  assert len(realScripts) == 470
  with open(os.path.join(dbmodule.BASE_DIR, "templates", "http.yaml"), encoding="utf-8") as f:
    arguments = yaml.safe_load(f)["http"]["arguments"]
  tokens = shlex.split(arguments)
  expression = tokens[tokens.index("--script") + 1]
  assert expression == "(http-*) and not (brute or dos or exploit or fuzzer or external)"
  analysis = analyzeScriptExpression(expression, realScripts, template=True)
  assert analysis["parsed"] is True
  assert analysis["blocked"] == set()
  excluded = {"brute", "dos", "exploit", "fuzzer", "external"}
  assert analysis["categories"] & excluded == set()
  assert all(not (realScripts[script] & excluded) for script in analysis["selected"])
  assert len(analysis["selected"]) == 63
  assert any("safe" not in realScripts[script] for script in analysis["selected"])
  assert analysis["unsafe"] is True and analysis["needsConfirm"] is True
  upperAnalysis = analyzeScriptExpression("(http-*) AND NOT (BRUTE OR DOS OR EXPLOIT OR FUZZER OR EXTERNAL)", realScripts, template=True)
  assert upperAnalysis["selected"] == analysis["selected"] and upperAnalysis["blockedSelected"] == set()
  monkeypatch.setattr(dbmodule, "scriptCategories", lambda: realScripts)
  monkeypatch.setattr("builtins.input", lambda prompt: "n")
  helpernmap.HelperNmap("template:http net:127.0.0.1").process()
  assert scanner.calls == []
  assert "Scan cancelled" in capsys.readouterr().out
  monkeypatch.setattr("builtins.input", lambda prompt: "y")
  helpernmap.HelperNmap("template:http net:127.0.0.1").process()
  assert scanner.calls == [("127.0.0.1", arguments)]

def test_template_safety_messages_exist_in_every_language():
  keys = (
    "help_run_plan", "help_run_reason", "help_run_reason_unsafe", "help_run_reason_external",
    "help_run_reason_not", "help_run_reason_unverified", "help_run_confirm",
    "help_run_cancelled", "help_run_blocked_scripts", "help_run_blocked_folder",
  )
  for lang in ("en", "es"):
    with open(os.path.join(dbmodule.BASE_DIR, "i18n", f"help.{lang}.yml"), encoding="utf-8") as f:
      messages = yaml.safe_load(f)[lang]
    for key in keys:
      assert messages.get(key)
