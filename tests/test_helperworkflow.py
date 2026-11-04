import nmap
import pytest
import re
import shlex
import yaml

import dbmodule
import helperworkflow

from helperworkflow import WorkflowError, validateArguments, validateWorkflow

SCRIPTS = {"http-title": {"default", "safe"}, "http-headers": {"discovery", "safe"}, "http-sql": {"intrusive", "vuln"},
  "http-slowloris": {"dos", "intrusive"}, "v-safe": {"safe", "vuln"}, "ssh-hostkey": {"default", "safe"},
  "ssh2-enum-algos": {"discovery", "safe"}, "bc": {"broadcast", "safe"}}

def args(arguments, source=None, confirm=False):
  return validateArguments(arguments, source, confirm, "15m", SCRIPTS)

class FakeHost(dict):
  def __init__(self, ports, state="up", hostname="", hostscript=None):
    self.ports = ports
    self.hostState = state
    self.name = hostname
    self.hostscript = hostscript
    if hostscript:
      dict.__init__(self, hostscript=hostscript)
  def hostname(self):
    return self.name
  def state(self):
    return self.hostState
  def all_protocols(self):
    return ["tcp"] if self.ports else []
  def __getitem__(self, key):
    return self.ports if key == "tcp" else dict.__getitem__(self, key)

class FakeScanner:
  def __init__(self):
    self.calls = []
    self.results = {}
    self.error = None
    self.current = {}
  def scan(self, hosts, ports=None, arguments=""):
    self.calls.append((hosts, ports, arguments))
    if self.error is not None and len(self.calls) >= self.error[0]:
      raise self.error[1]
    self.current = self.results[len(self.calls) - 1] if len(self.calls) - 1 in self.results else {}
  def all_hosts(self):
    return list(self.current)
  def __getitem__(self, host):
    return self.current[host]

@pytest.fixture
def scanner(monkeypatch):
  fake = FakeScanner()
  monkeypatch.setattr(nmap, "PortScanner", lambda: fake)
  return fake

@pytest.fixture
def workflows(tmp_path, monkeypatch):
  monkeypatch.setattr(helperworkflow, "WORKFLOWS_DIR", str(tmp_path))
  def write(name, stages):
    (tmp_path / (name + ".yaml")).write_text(yaml.safe_dump({name: {"stages": stages}}), encoding="utf-8")
  return write

@pytest.fixture
def answers(monkeypatch):
  given = []
  def fake(message):
    return given.pop(0)
  monkeypatch.setattr("builtins.input", fake)
  return given

CHAIN = [
  {"name": "discovery", "arguments": "-sn"},
  {"name": "ports", "from": "live_hosts", "arguments": "-F"},
  {"name": "services", "from": "open_ports", "arguments": "-sV"},
  {"name": "enum", "from": "services", "when": {"service": ["http"]}, "arguments": "--script http-title"},
]

# ---- Option validation

@pytest.mark.parametrize("arguments", [
  "-sV 8.8.8.8", "-oN /tmp/x", "-oX -", "-oA x", "-iL /etc/passwd", "-iR 100", "--resume x", "--datadir /tmp",
  "--excludefile x", "--stylesheet x", "--script-args-file x", "-sU", "-sC", "-A", "-D 1.1.1.1", "-S 1.1.1.1",
  "--proxies x", "-p22", "--foo", "--top-ports", "--top-ports 'a b'", "-sV 'unclosed",
])
def test_options_outside_the_allowlist_are_rejected(arguments):
  with pytest.raises(WorkflowError):
    args(arguments, "live_hosts")

def test_valid_arguments_and_default_timeout():
  assert args("-sV -T4 --top-ports=100", "live_hosts") == "-sV -T4 --top-ports 100 --host-timeout 15m"
  assert args("-sn --host-timeout 1m") == "-sn --host-timeout 1m"

@pytest.mark.parametrize("arguments", ["-p 80", "--top-ports 10", "-F"])
def test_later_stages_cannot_widen_the_ports(arguments):
  for source in ("open_ports", "services"):
    with pytest.raises(WorkflowError):
      args(arguments, source)

# ---- Script validation

def test_safe_scripts_need_no_confirmation_and_blocked_are_excluded():
  result = args("--script http-headers,http-title", "services")
  assert "(http-headers or http-title) and not (broadcast or dos)" in result

@pytest.mark.parametrize("expression", ["http-sql", "vuln", "http-*", "not safe", "safe and not http-title", "intrusive"])
def test_unsafe_scripts_require_confirm(expression):
  with pytest.raises(WorkflowError, match="confirm"):
    args("--script '" + expression + "'", "services")
  assert "and not (broadcast or dos)" in args("--script '" + expression + "'", "services", True)

@pytest.mark.parametrize("expression", ["dos", "broadcast", "http-slowloris", "http-title or dos", "unknown-script", "/tmp/evil.lua", "../x", "http-title;id"])
def test_forbidden_scripts_are_rejected_even_with_confirm(expression):
  with pytest.raises(WorkflowError):
    args("--script '" + expression + "'", "services", True)

@pytest.mark.parametrize("expression", ["bc) or (http-title", "vuln) or (http-title", "(http-title", "http-title)", "http-title) or (", ")("])
def test_unbalanced_expressions_cannot_escape_the_exclusions(expression):
  for confirm in (False, True):
    with pytest.raises(WorkflowError):
      args("--script '" + expression + "'", "services", confirm)

def test_script_args_rules():
  with pytest.raises(WorkflowError):
    args("--script http-title --script-args a=1", "services")
  with pytest.raises(WorkflowError):
    args("--script-args newtargets", "services", True)
  assert "--script-args a=1" in args("--script-args a=1", "services", True)

# ---- Workflow structure

@pytest.mark.parametrize("stages", [
  [],
  "x",
  [{"name": "a"}],
  [{"arguments": "-sn"}],
  [{"name": "a", "arguments": "-sn", "from": "live_hosts"}],
  [{"name": "a", "arguments": "-sn"}, {"name": "b", "arguments": "-F"}],
  [{"name": "a", "arguments": "-sn"}, {"name": "b", "from": "nope", "arguments": "-F"}],
  [{"name": "a", "arguments": "-sn"}, {"name": "a", "from": "live_hosts", "arguments": "-F"}],
  [{"name": "../a", "arguments": "-sn"}],
  [{"name": "a", "arguments": "-sn", "extra": 1}],
  [{"name": "a", "arguments": "-sn", "host_timeout": "1; id"}],
  [{"name": "a", "arguments": "-sn"}, {"name": "b", "from": "live_hosts", "when": {"service": ["http"]}, "arguments": "-F"}],
  [{"name": "a", "arguments": "-sn"}, {"name": "b", "from": "services", "when": "http", "arguments": "-sV"}],
])
def test_invalid_workflows_are_rejected(stages):
  with pytest.raises(WorkflowError):
    validateWorkflow("w", {"w": {"stages": stages}}, SCRIPTS)

@pytest.mark.parametrize("name", ["basic", "ssh", "web"])
def test_shipped_workflows_are_valid(name):
  scripts = dict(SCRIPTS, v={"vuln"})
  with open(helperworkflow.os.path.join(helperworkflow.BASE_DIR, "workflows", name + ".yaml"), encoding="utf-8") as f:
    stages = validateWorkflow(name, yaml.safe_load(f), scripts)
  assert stages[0]["source"] is None
  assert all(stage["confirm"] for stage in stages if "vuln" in stage["arguments"])

@pytest.mark.parametrize("name", ["../../x", "a/b", "nope", ""])
def test_unknown_workflow_names_do_not_scan(db, scanner, capsys, workflows, name):
  helperworkflow.HelperWorkflow("name:" + name + " net:127.0.0.1", "run").process()
  assert scanner.calls == []

# ---- Execution

def chainResults():
  return {
    0: {"10.0.0.1": FakeHost({}), "10.0.0.2": FakeHost({}, state="down"), "10.0.0.3": FakeHost({})},
    1: {"10.0.0.1": FakeHost({22: {"state": "open", "name": "ssh"}, 80: {"state": "open", "name": "http"}, 81: {"state": "closed", "name": ""}})},
    2: {"10.0.0.3": FakeHost({})},
    3: {"10.0.0.1": FakeHost({22: {"state": "open", "name": "ssh", "product": "OpenSSH", "version": "9"}, 80: {"state": "open", "name": "http", "product": "nginx", "version": "1"}})},
    4: {"10.0.0.1": FakeHost({80: {"state": "open", "name": "http", "script": {"http-title": "Home"}}})},
  }

def test_each_stage_only_scans_what_was_found(db, scanner, workflows, answers, monkeypatch):
  workflows("w", CHAIN)
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  scanner.results = chainResults()
  answers.append("y")
  helperworkflow.HelperWorkflow("name:w net:10.0.0.0/24", "run").process()
  calls = [(hosts, ports) for hosts, ports, _ in scanner.calls]
  assert calls == [("10.0.0.0/24", None), ("10.0.0.1", None), ("10.0.0.3", None), ("10.0.0.1", "22,80"), ("10.0.0.1", "80")]
  details = db.getRun(1)
  assert details["run"]["status"] == "completed"
  assert details["findings"][0]["output"] == "Home"
  assert [stage["status"] for stage in details["stages"]] == ["completed"] * 4

def test_no_scan_without_initial_confirmation(db, scanner, workflows, answers, monkeypatch, capsys):
  workflows("w", CHAIN)
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  answers.append("n")
  helperworkflow.HelperWorkflow("name:w net:10.0.0.1", "run").process()
  assert scanner.calls == []
  assert db.getRuns() == []

def test_end_of_input_counts_as_no(monkeypatch):
  def eof(message):
    raise EOFError
  monkeypatch.setattr("builtins.input", eof)
  assert not helperworkflow.askConfirmation("x")

@pytest.mark.parametrize("net", ["-oN/tmp/x", "--script=x", "a b"])
def test_bad_targets_are_rejected(db, scanner, workflows, answers, net, monkeypatch):
  workflows("w", CHAIN)
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  helperworkflow.HelperWorkflow('name:w "net:' + net + '"', "run").process()
  assert scanner.calls == []

def test_results_outside_the_scope_are_ignored(db, scanner, workflows, answers, monkeypatch, capsys):
  workflows("w", CHAIN[:3])
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  scanner.results = {
    0: {"10.0.0.1": FakeHost({})},
    1: {"10.0.0.1": FakeHost({80: {"state": "open", "name": "http"}}), "8.8.8.8": FakeHost({53: {"state": "open", "name": "domain"}}), "not-an-ip": FakeHost({})},
  }
  answers.append("y")
  helperworkflow.HelperWorkflow("name:w net:10.0.0.0/24", "run").process()
  assert "Ignored result" in capsys.readouterr().out
  assert all(hosts == "10.0.0.1" for hosts, ports, _ in scanner.calls[1:])
  assert [host["address"] for host in db.getRun(1)["hosts"]] == ["10.0.0.1"]

def test_remote_data_never_reaches_nmap_arguments(db, scanner, workflows, answers, monkeypatch, capsys):
  workflows("w", CHAIN)
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  evil = "http --script=dos\x1b[2J"
  scanner.results = {
    0: {"10.0.0.1": FakeHost({}, hostname="evil\x1b[2J -oN/tmp/x")},
    1: {"10.0.0.1": FakeHost({80: {"state": "open", "name": evil, "product": "\x1b]0;x", "version": "--script=dos"}})},
  }
  answers.append("y")
  helperworkflow.HelperWorkflow("name:w net:10.0.0.1", "run").process()
  assert "\x1b" not in capsys.readouterr().out
  for hosts, ports, arguments in scanner.calls:
    assert "evil" not in hosts + arguments
    assert "--script=dos" not in arguments
  assert len(scanner.calls) == 3
  assert db.getRun(1)["stages"][3]["status"] == "skipped"

def test_when_filters_services(db, scanner, workflows, answers, monkeypatch):
  workflows("w", CHAIN)
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  scanner.results = {
    0: {"10.0.0.1": FakeHost({})},
    1: {"10.0.0.1": FakeHost({22: {"state": "open", "name": "ssh"}})},
    2: {"10.0.0.1": FakeHost({22: {"state": "open", "name": "ssh"}})},
  }
  answers.append("y")
  helperworkflow.HelperWorkflow("name:w net:10.0.0.1", "run").process()
  assert len(scanner.calls) == 3
  assert db.getRun(1)["stages"][3]["status"] == "skipped"

@pytest.mark.parametrize("answer,expected", [("n", "declined"), ("", "declined"), ("y", "completed")])
def test_intrusive_stage_confirmation(db, scanner, workflows, answers, monkeypatch, answer, expected):
  stages = CHAIN[:3] + [{"name": "vuln", "from": "services", "arguments": "--script http-sql", "confirm": True}]
  workflows("w", stages)
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  scanner.results = {0: {"10.0.0.1": FakeHost({})}, 1: {"10.0.0.1": FakeHost({80: {"state": "open", "name": "http"}})}}
  answers += ["y", answer]
  helperworkflow.HelperWorkflow("name:w net:10.0.0.1", "run").process()
  assert db.getRun(1)["stages"][3]["status"] == expected
  assert len(scanner.calls) == (4 if expected == "completed" else 3)

@pytest.mark.parametrize("error,status,message", [
  (nmap.PortScannerError("bad"), "failed", "The scan failed"),
  (KeyboardInterrupt(), "interrupted", "Scan interrupted"),
])
def test_failures_keep_earlier_results(db, scanner, workflows, answers, monkeypatch, capsys, error, status, message):
  workflows("w", CHAIN)
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  scanner.results = {0: {"10.0.0.1": FakeHost({})}}
  scanner.error = (2, error)
  answers.append("y")
  helperworkflow.HelperWorkflow("name:w net:10.0.0.1", "run").process()
  assert message in capsys.readouterr().out
  details = db.getRun(1)
  assert details["run"]["status"] == status
  assert [host["address"] for host in details["hosts"]] == ["10.0.0.1"]
  assert details["stages"][0]["status"] == "completed"
  assert details["stages"][1]["status"] == status

def test_storage_errors_mark_the_run_as_failed(db, scanner, workflows, answers, monkeypatch, capsys):
  workflows("w", CHAIN)
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  scanner.results = {0: {"10.0.0.1": FakeHost({})}}
  answers.append("y")
  def fail(*args):
    raise dbmodule.lite.OperationalError("disk full")
  monkeypatch.setattr(db, "saveStageResults", fail)
  helperworkflow.HelperWorkflow("name:w net:10.0.0.1", "run").process()
  assert "disk full" in capsys.readouterr().out
  details = db.getRun(1)
  assert details["run"]["status"] == "failed"
  assert details["stages"][0]["status"] == "failed"

def test_interrupted_confirmation_counts_as_no(monkeypatch):
  def interrupt(message):
    raise KeyboardInterrupt
  monkeypatch.setattr("builtins.input", interrupt)
  assert not helperworkflow.askConfirmation("x")

def test_missing_nmap(db, workflows, answers, monkeypatch, capsys):
  workflows("w", CHAIN)
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  def missing():
    raise nmap.PortScannerError("not found")
  monkeypatch.setattr(nmap, "PortScanner", missing)
  answers.append("y")
  helperworkflow.HelperWorkflow("name:w net:10.0.0.1", "run").process()
  assert "nmap was not found" in capsys.readouterr().out

def test_ipv6_targets_use_the_ipv6_option(db, scanner, workflows, answers, monkeypatch):
  workflows("w", CHAIN[:2])
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)
  scanner.results = {0: {"fe80::1": FakeHost({})}}
  answers.append("y")
  helperworkflow.HelperWorkflow("name:w net:fe80::1", "run").process()
  assert all(arguments.startswith("-6 ") for _, _, arguments in scanner.calls)
  assert scanner.calls[1][0] == "fe80::1"

@pytest.mark.parametrize("command,args", [("", ""), ("nope", ""), ("run", ""), ("run", "name:w"), ("run", "foo:bar"), ("status", "id:x"), ("status", "foo:1")])
def test_invalid_commands_do_not_raise(db, scanner, command, args, capsys):
  helperworkflow.HelperWorkflow(args, command).process()
  assert "help workflow" in capsys.readouterr().out
  assert scanner.calls == []

def test_list_and_status(db, workflows, capsys):
  workflows("w", CHAIN)
  helperworkflow.HelperWorkflow("", "list").process()
  assert "[+] w" in capsys.readouterr().out
  helperworkflow.HelperWorkflow("id:99", "status").process()
  assert "not found" in capsys.readouterr().out
  db.createRun("web\x1b[2J", "10.0.0.1", [])
  helperworkflow.HelperWorkflow("", "status").process()
  assert "\x1b" not in capsys.readouterr().out
  helperworkflow.HelperWorkflow("id:1", "status").process()
  assert "\x1b" not in capsys.readouterr().out

# ---- Resume

def savedRun(db, statuses, net="10.0.0.0/24", runStatus="interrupted", stages=CHAIN, name="w", workflows=None):
  workflows(name, stages)
  loaded = helperworkflow.loadWorkflow(name, SCRIPTS)
  runId = db.createRun(name, net, loaded)
  for position, status in enumerate(statuses):
    db.setStageStatus(runId, position, status)
  db.setRunStatus(runId, runStatus)
  return runId

def resume(runId=1):
  helperworkflow.HelperWorkflow("id:" + str(runId), "resume").process()

@pytest.fixture
def catalog(db, monkeypatch):
  monkeypatch.setattr(db, "scriptCategories", lambda: SCRIPTS)

def foundFirstStage(db, runId, addresses=("10.0.0.1",)):
  db.saveStageResults(runId, "discovery", [{"address": address, "hostname": "", "state": "up"} for address in addresses], [], [])

@pytest.mark.parametrize("args,message", [("", "help workflow"), ("foo:1", "help workflow"), ("id:x", "help workflow"), ("id:-1", "help workflow"),
  ("id:\u00b2", "help workflow"), ("id:" + "9" * 30, "help workflow"), ("id:99", "not found")])
def test_resume_rejects_bad_ids(db, scanner, capsys, args, message):
  helperworkflow.HelperWorkflow(args, "resume").process()
  assert message in capsys.readouterr().out
  assert scanner.calls == []

def test_status_rejects_ids_it_cannot_look_up(db, capsys):
  for value in ("\u00b2", "9" * 30):
    helperworkflow.HelperWorkflow("id:" + value, "status").process()
    assert "help workflow" in capsys.readouterr().out

def test_completed_runs_cannot_be_resumed(db, scanner, workflows, catalog, capsys):
  savedRun(db, ["completed"] * 4, runStatus="completed", workflows=workflows)
  resume()
  assert "cannot be resumed" in capsys.readouterr().out
  assert scanner.calls == []

@pytest.mark.parametrize("runStatus,stageStatus", [("interrupted", "interrupted"), ("failed", "failed"), ("running", "running")])
def test_resume_continues_each_resumable_status(db, scanner, workflows, answers, catalog, runStatus, stageStatus):
  runId = savedRun(db, ["completed", stageStatus], runStatus=runStatus, workflows=workflows)
  foundFirstStage(db, runId)
  scanner.results = {0: {"10.0.0.1": FakeHost({80: {"state": "open", "name": "http"}})}, 1: {"10.0.0.1": FakeHost({80: {"state": "open", "name": "http"}})}}
  answers.append("y")
  resume(runId)
  assert [(hosts, ports) for hosts, ports, _ in scanner.calls] == [("10.0.0.1", None), ("10.0.0.1", "80"), ("10.0.0.1", "80")]
  details = db.getRun(runId)
  assert details["run"]["status"] == "completed" and details["run"]["finished_at"]
  assert [stage["status"] for stage in details["stages"]] == ["completed"] * 4

@pytest.mark.parametrize("status,runs", [("completed", False), ("skipped", False), ("declined", False),
  ("pending", True), ("running", True), ("interrupted", True), ("failed", True)])
def test_only_unfinished_stages_run_again(db, scanner, workflows, answers, catalog, status, runs):
  stages = [{"name": "discovery", "arguments": "-sn"}, {"name": "ports", "from": "live_hosts", "arguments": "-F"}]
  runId = savedRun(db, ["completed", status], stages=stages, workflows=workflows)
  foundFirstStage(db, runId)
  answers.append("y")
  resume(runId)
  assert len(scanner.calls) == (1 if runs else 0)
  assert db.getRun(runId)["run"]["status"] == "completed"
  assert db.getRun(runId)["stages"][1]["status"] == ("completed" if runs else status)

def test_nothing_left_completes_without_asking(db, scanner, workflows, catalog, capsys):
  runId = savedRun(db, ["completed"] * 4, runStatus="running", workflows=workflows)
  resume(runId)
  assert "No stages left" in capsys.readouterr().out
  assert scanner.calls == []
  assert db.getRun(runId)["run"]["status"] == "completed"

def test_resume_shows_the_target_and_remaining_stages(db, scanner, workflows, catalog, monkeypatch, capsys):
  runId = savedRun(db, ["completed", "completed"], workflows=workflows)
  asked = []
  monkeypatch.setattr("builtins.input", lambda message: asked.append(message) or "n")
  resume(runId)
  out = capsys.readouterr().out
  assert "10.0.0.0/24" in out and "services" in out and "enum" in out
  assert "discovery" not in out and "ports:" not in out
  assert "authorized" in asked[0]

@pytest.mark.parametrize("answer", ["n", "", EOFError, KeyboardInterrupt])
def test_refusing_to_resume_changes_nothing(db, scanner, workflows, catalog, monkeypatch, capsys, answer):
  runId = savedRun(db, ["completed", "interrupted"], workflows=workflows)
  before = db.getRun(runId)
  def respond(message):
    if isinstance(answer, str):
      return answer
    raise answer
  monkeypatch.setattr("builtins.input", respond)
  resume(runId)
  assert "cancelled" in capsys.readouterr().out
  assert scanner.calls == []
  assert db.getRun(runId) == before

CONFIRMED = CHAIN[:3] + [{"name": "vuln", "from": "services", "arguments": "--script http-sql", "confirm": True}]

@pytest.mark.parametrize("answer,expected,scans", [("y", "completed", 1), ("n", "declined", 0)])
def test_intrusive_stages_ask_again(db, scanner, workflows, answers, catalog, answer, expected, scans):
  runId = savedRun(db, ["completed", "completed", "completed", "interrupted"], stages=CONFIRMED, workflows=workflows)
  foundFirstStage(db, runId)
  db.saveStageResults(runId, "ports", [], [{"address": "10.0.0.1", "protocol": "tcp", "port": 80, "state": "open", "service": "http", "product": "", "version": ""}], [])
  answers += ["y", answer]
  resume(runId)
  assert answers == []
  assert len(scanner.calls) == scans
  assert db.getRun(runId)["stages"][3]["status"] == expected
  assert db.getRun(runId)["run"]["status"] == "completed"

def test_declined_stages_do_not_ask_again(db, scanner, workflows, answers, catalog):
  runId = savedRun(db, ["completed", "completed", "completed", "declined"], stages=CONFIRMED, runStatus="running", workflows=workflows)
  resume(runId)
  assert scanner.calls == []
  assert db.getRun(runId)["run"]["status"] == "completed"

def test_unfinished_first_stage_uses_the_original_network(db, scanner, workflows, answers, catalog):
  runId = savedRun(db, ["interrupted"], stages=CHAIN[:2], workflows=workflows)
  scanner.results = {0: {"10.0.0.7": FakeHost({})}}
  answers.append("y")
  resume(runId)
  assert [hosts for hosts, _, _ in scanner.calls] == ["10.0.0.0/24", "10.0.0.7"]

def test_resume_keeps_the_scope_of_the_run(db, scanner, workflows, answers, catalog, capsys):
  runId = savedRun(db, ["completed", "interrupted"], stages=CHAIN[:3], workflows=workflows)
  foundFirstStage(db, runId)
  scanner.results = {0: {"10.0.0.1": FakeHost({80: {"state": "open", "name": "http"}}), "8.8.8.8": FakeHost({53: {"state": "open", "name": "domain"}})},
    1: {"8.8.8.8": FakeHost({53: {"state": "open", "name": "domain"}})}}
  answers.append("y")
  resume(runId)
  assert "Ignored result" in capsys.readouterr().out
  assert [host["address"] for host in db.getRun(runId)["hosts"]] == ["10.0.0.1"]
  assert [hosts for hosts, _, _ in scanner.calls] == ["10.0.0.1", "10.0.0.1"]

def test_declining_a_repeated_first_stage_keeps_the_scope(db, scanner, workflows, answers, catalog):
  stages = [{"name": "discovery", "arguments": "-sn", "confirm": True}, CHAIN[1]]
  runId = savedRun(db, ["running"], stages=stages, workflows=workflows)
  foundFirstStage(db, runId)
  scanner.results = {0: {"8.8.8.8": FakeHost({})}}
  answers += ["y", "n"]
  resume(runId)
  assert [hosts for hosts, _, _ in scanner.calls] == ["10.0.0.1"]
  assert [host["address"] for host in db.getRun(runId)["hosts"]] == ["10.0.0.1"]

@pytest.mark.parametrize("net", ["-oN/tmp/x", "--script=x", "a b", "10.0.0.1;id"])
def test_saved_targets_are_validated_again(db, scanner, workflows, catalog, capsys, net):
  runId = savedRun(db, ["interrupted"], net=net, workflows=workflows)
  before = db.getRun(runId)
  resume(runId)
  assert "Invalid target" in capsys.readouterr().out
  assert scanner.calls == []
  assert db.getRun(runId) == before

@pytest.mark.parametrize("changed", [
  [CHAIN[1], CHAIN[0]] + CHAIN[2:],
  CHAIN[:3],
  CHAIN + [{"name": "extra", "from": "services", "arguments": "--script http-headers"}],
  [dict(CHAIN[0], name="renamed")] + CHAIN[1:],
  CHAIN[:1] + [dict(CHAIN[1], arguments="--top-ports 10")] + CHAIN[2:],
  CHAIN[:2] + [dict(CHAIN[2], **{"from": "live_hosts"})] + CHAIN[3:],
  CHAIN[:3] + [dict(CHAIN[3], when={"service": ["ssh"]})],
  CHAIN[:2] + [dict(CHAIN[2], confirm=True)] + CHAIN[3:],
  CHAIN[:2] + [dict(CHAIN[2], host_timeout="1m")] + CHAIN[3:],
])
def test_changed_workflows_are_rejected(db, scanner, workflows, catalog, capsys, changed):
  runId = savedRun(db, ["completed", "interrupted"], workflows=workflows)
  before = db.getRun(runId)
  workflows("w", changed)
  resume(runId)
  out = capsys.readouterr().out
  assert "changed" in out or "not valid" in out
  assert scanner.calls == []
  assert db.getRun(runId) == before

def test_removing_a_confirmation_or_widening_the_ports_is_rejected(db, scanner, workflows, catalog, capsys):
  stages = CHAIN[:3] + [{"name": "inspect", "from": "services", "when": {"service": ["ssh"]}, "arguments": "-sV", "confirm": True}]
  runId = savedRun(db, ["completed", "completed", "completed", "interrupted"], stages=stages, workflows=workflows)
  foundFirstStage(db, runId)
  workflows("w", CHAIN[:3] + [{"name": "inspect", "from": "live_hosts", "arguments": "-sV"}])
  resume(runId)
  assert "changed" in capsys.readouterr().out
  assert scanner.calls == []

def test_runs_from_earlier_versions_cannot_be_resumed(db, scanner, workflows, catalog, capsys):
  runId = savedRun(db, ["completed", "interrupted"], workflows=workflows)
  conn = dbmodule.lite.connect(dbmodule.dbname)
  conn.execute("ALTER TABLE workflow_stages DROP COLUMN definition")
  conn.commit()
  conn.close()
  resume(runId)
  assert "changed" in capsys.readouterr().out
  assert scanner.calls == []
  assert db.getRun(runId)["stages"][0]["definition"] is None

@pytest.mark.parametrize("status", ["interrupted", "failed"])
def test_two_consoles_cannot_resume_the_same_run(db, scanner, workflows, catalog, monkeypatch, capsys, status):
  runId = savedRun(db, ["completed", status], runStatus=status, workflows=workflows)
  def otherConsoleWins(message):
    assert db.claimRun(runId, status)
    return "y"
  monkeypatch.setattr("builtins.input", otherConsoleWins)
  resume(runId)
  assert "already resumed" in capsys.readouterr().out
  assert scanner.calls == []

def test_running_runs_warn_before_resuming(db, scanner, workflows, answers, catalog, capsys):
  runId = savedRun(db, ["completed", "running"], runStatus="running", workflows=workflows)
  answers.append("n")
  resume(runId)
  assert "no other console" in capsys.readouterr().out
  assert scanner.calls == []

def test_workflows_that_are_no_longer_valid_are_rejected(db, scanner, workflows, catalog, capsys, tmp_path):
  runId = savedRun(db, ["completed", "interrupted"], workflows=workflows)
  before = db.getRun(runId)
  for content in ("w:\n  stages:\n    - name: discovery\n      arguments: '-oN /tmp/x'\n", "not: [valid", None):
    if content is None:
      (tmp_path / "w.yaml").unlink()
    else:
      (tmp_path / "w.yaml").write_text(content, encoding="utf-8")
    resume(runId)
    assert "not valid" in capsys.readouterr().out
  assert scanner.calls == []
  assert db.getRun(runId) == before

def test_saved_workflow_names_cannot_leave_the_directory(db, scanner, workflows, catalog, capsys):
  db.createRun("../../x", "10.0.0.1", [])
  db.setRunStatus(1, "failed")
  resume()
  assert "not valid" in capsys.readouterr().out
  assert scanner.calls == []

def test_repeating_a_stage_does_not_duplicate_findings(db, scanner, workflows, answers, catalog):
  stages = [CHAIN[0], {"name": "enum", "from": "live_hosts", "arguments": "--script http-title"}]
  runId = savedRun(db, ["completed", "interrupted"], stages=stages, workflows=workflows)
  foundFirstStage(db, runId)
  db.saveStageResults(runId, "enum", [{"address": "10.0.0.1", "hostname": "", "state": "up"}], [],
    [{"address": "10.0.0.1", "port": None, "script": "old", "output": "old"}, {"address": "10.0.0.1", "port": 80, "script": "http-title", "output": "old"}])
  scanner.results = {0: {"10.0.0.1": FakeHost({80: {"state": "open", "name": "http", "script": {"http-title": "new"}}})}}
  answers.append("y")
  resume(runId)
  assert [(item["script"], item["output"]) for item in db.getRun(runId)["findings"]] == [("http-title", "new")]

def test_interrupt_keeps_finished_targets_and_can_resume(db, scanner, workflows, answers, catalog, capsys):
  stages = [CHAIN[0], {"name": "enum", "from": "live_hosts", "arguments": "--script http-title"}]
  workflows("w", stages)
  host = lambda title: FakeHost({80: {"state": "open", "name": "http", "script": {"http-title": title}}})
  scanner.results = {0: {"10.0.0.1": FakeHost({}), "10.0.0.2": FakeHost({})}, 1: {"10.0.0.1": host("one")}, 3: {"10.0.0.1": host("one")}, 4: {"10.0.0.2": host("two")}}
  scanner.error = (3, KeyboardInterrupt())
  answers.append("y")
  helperworkflow.HelperWorkflow("name:w net:10.0.0.0/24", "run").process()
  assert "workflow resume id:1" in capsys.readouterr().out
  details = db.getRun(1)
  assert details["run"]["status"] == "interrupted"
  assert details["stages"][1]["status"] == "interrupted"
  assert [item["address"] for item in details["findings"]] == ["10.0.0.1"]
  scanner.error = None
  answers.append("y")
  resume()
  details = db.getRun(1)
  assert details["run"]["status"] == "completed"
  assert sorted((item["address"], item["output"]) for item in details["findings"]) == [("10.0.0.1", "one"), ("10.0.0.2", "two")]
  assert [hosts for hosts, _, _ in scanner.calls] == ["10.0.0.0/24", "10.0.0.1", "10.0.0.2", "10.0.0.1", "10.0.0.2"]

@pytest.mark.parametrize("error,status", [(nmap.PortScannerError("bad"), "failed"), (KeyboardInterrupt(), "interrupted")])
def test_a_resumed_run_can_stop_and_resume_again(db, scanner, workflows, answers, catalog, error, status):
  runId = savedRun(db, ["completed", "failed"], stages=CHAIN[:2], runStatus="failed", workflows=workflows)
  foundFirstStage(db, runId)
  scanner.error = (1, error)
  answers.append("y")
  resume(runId)
  details = db.getRun(runId)
  assert details["run"]["status"] == status and details["stages"][1]["status"] == status
  assert details["run"]["finished_at"]
  scanner.error = None
  answers.append("y")
  resume(runId)
  assert db.getRun(runId)["run"]["status"] == "completed"

def test_resume_without_nmap_changes_nothing(db, workflows, answers, catalog, monkeypatch, capsys):
  runId = savedRun(db, ["completed", "interrupted"], workflows=workflows)
  before = db.getRun(runId)
  def missing():
    raise nmap.PortScannerError("not found")
  monkeypatch.setattr(nmap, "PortScanner", missing)
  answers.append("y")
  resume(runId)
  assert "nmap was not found" in capsys.readouterr().out
  assert db.getRun(runId) == before

def test_resume_does_not_print_control_characters(db, scanner, workflows, answers, catalog, capsys):
  runId = savedRun(db, ["completed", "interrupted"], stages=CHAIN[:2], workflows=workflows)
  foundFirstStage(db, runId)
  scanner.results = {0: {"10.0.0.1": FakeHost({80: {"state": "open", "name": "http\x1b[2J", "product": "\x1b]0;x"}}, hostname="evil\x1b[2J")}}
  answers.append("y")
  resume(runId)
  assert "\x1b" not in capsys.readouterr().out

def installedScripts():
  for path in ("/opt/homebrew/share/nmap/scripts/script.db", "/usr/local/share/nmap/scripts/script.db", "/usr/share/nmap/scripts/script.db"):
    if helperworkflow.os.path.exists(path):
      with open(path, encoding="utf-8") as f:
        return {name: set(re.findall(r'"([a-z]+)"', categories)) for name, categories in re.findall(r'filename = "([^"]+)\.nse", categories = \{([^}]*)\}', f.read())}
  pytest.skip("nmap is not installed")

def test_smb_only_uses_safe_scripts_for_smb_services():
  with open(helperworkflow.os.path.join(helperworkflow.BASE_DIR, "workflows", "smb.yaml"), encoding="utf-8") as f:
    content = yaml.safe_load(f)
  stages = content["smb"]["stages"]
  assert not any(stage.get("confirm") for stage in stages)
  assert stages[-1]["when"] == {"service": ["microsoft-ds", "netbios-ssn"]}
  installed = installedScripts()
  for script in stages[-1]["arguments"].split()[1].split(","):
    assert "safe" in installed[script]
  validateWorkflow("smb", content, installed)

def test_resume_messages_exist_in_every_language():
  for language in ("en", "es"):
    with open(helperworkflow.os.path.join(helperworkflow.BASE_DIR, "i18n", "help." + language + ".yml"), encoding="utf-8") as f:
      messages = yaml.safe_load(f)[language]
    for key in ("workflow_not_resumable", "workflow_changed", "workflow_resume_nothing", "workflow_resume_hint", "workflow_resume_running", "workflow_already_resumed"):
      assert messages[key]

def test_a_resumed_run_is_running_while_it_scans(db, scanner, workflows, answers, catalog, monkeypatch):
  runId = savedRun(db, ["completed", "interrupted"], stages=CHAIN[:2], workflows=workflows)
  foundFirstStage(db, runId)
  seen = []
  monkeypatch.setattr(scanner, "scan", lambda hosts, ports=None, arguments="": seen.append(db.getRun(runId)["run"]))
  answers.append("y")
  resume(runId)
  assert seen[0]["status"] == "running" and seen[0]["finished_at"] is None

# ---- Reports

import json
import os
import stat

HTTP_HOST = {"10.0.0.1": FakeHost({80: {"state": "open", "name": "http", "product": "nginx", "version": "1.0", "script": {"http-title": "Welcome"}}})}

@pytest.fixture
def reports(tmp_path, monkeypatch):
  folder = tmp_path / "reports"
  monkeypatch.setattr(helperworkflow, "REPORTS_DIR", str(folder))
  return folder

def report(runId=1, extension="md"):
  helperworkflow.HelperWorkflow("id:%d format:%s" % (runId, extension), "report").process()

def fullRun(scanner, workflows, answers, stages=CHAIN, results=None, name="w", net="10.0.0.0/24"):
  workflows(name, stages)
  scanner.calls = []
  scanner.results = results if results is not None else {0: {"10.0.0.1": FakeHost({})}, 1: HTTP_HOST, 2: HTTP_HOST, 3: HTTP_HOST}
  answers.append("y")
  helperworkflow.HelperWorkflow("name:%s net:%s" % (name, net), "run").process()

def test_report_explains_why_each_stage_ran_and_on_what(db, scanner, workflows, answers, catalog, reports):
  fullRun(scanner, workflows, answers)
  report()
  text = (reports / "workflow-1.md").read_text(encoding="utf-8")
  sections = re.split(r"^### ", text, flags=re.M)
  assert "First stage" in sections[1] and "` 10.0.0.0/24 `" in sections[1]
  assert "live hosts" in sections[2] and "` 10.0.0.1 `" in sections[2]
  assert "open ports" in sections[3] and "` 80 `" in sections[3]
  assert "with these services: http" in sections[4] and "` 80 `" in sections[4] and "http-title" in sections[4]
  assert "Welcome" in text and "nginx" in text

def test_report_says_why_a_stage_did_not_run(db, scanner, workflows, answers, catalog, reports):
  stages = CHAIN[:3] + [{"name": "vuln", "from": "services", "arguments": "--script http-sql", "confirm": True},
    {"name": "ssh", "from": "services", "when": {"service": ["ssh"]}, "arguments": "--script ssh-hostkey"}]
  answers.append("y")
  answers.append("n")
  workflows("w", stages)
  scanner.results = {0: {"10.0.0.1": FakeHost({})}, 1: HTTP_HOST, 2: HTTP_HOST}
  helperworkflow.HelperWorkflow("name:w net:10.0.0.0/24", "run").process()
  report(extension="json")
  found = json.loads((reports / "workflow-1.json").read_text(encoding="utf-8"))["stages"]
  assert "not confirmed" in found[3]["reason"] and found[3]["targets"] == [{"target": "10.0.0.1", "ports": "80"}]
  assert "nothing to scan" in found[4]["reason"] and found[4]["targets"] == []

def test_report_says_a_stage_was_confirmed(db, scanner, workflows, answers, catalog, reports):
  stages = CHAIN[:3] + [{"name": "vuln", "from": "services", "arguments": "--script http-sql", "confirm": True}]
  answers.append("y")
  fullRun(scanner, workflows, answers, stages=stages)
  report(extension="json")
  assert "it was confirmed" in json.loads((reports / "workflow-1.json").read_text(encoding="utf-8"))["stages"][3]["reason"]

@pytest.mark.parametrize("extension", ["md", "json"])
@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
def test_reports_are_only_readable_by_their_owner(db, scanner, workflows, answers, catalog, reports, extension):
  fullRun(scanner, workflows, answers)
  report(extension=extension)
  report(extension=extension)
  assert stat.S_IMODE(os.stat(reports / ("workflow-1." + extension)).st_mode) == 0o600
  assert stat.S_IMODE(os.stat(reports).st_mode) == 0o700
  assert os.listdir(reports) == ["workflow-1." + extension]

@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
def test_report_replaces_a_symlink_instead_of_following_it(db, scanner, workflows, answers, catalog, reports, tmp_path):
  fullRun(scanner, workflows, answers)
  reports.mkdir()
  victim = tmp_path / "victim"
  victim.write_text("original", encoding="utf-8")
  (reports / "workflow-1.md").symlink_to(victim)
  report()
  assert victim.read_text(encoding="utf-8") == "original"
  assert not (reports / "workflow-1.md").is_symlink()

@pytest.mark.parametrize("args", ["", "format:md", "id:x", "id:1 format:html", "id:1 format:../../x", "id:1 path:/tmp/x", "id:" + "9" * 30])
def test_report_rejects_bad_arguments(db, reports, capsys, args):
  helperworkflow.HelperWorkflow(args, "report").process()
  assert "help workflow" in capsys.readouterr().out
  assert not reports.exists()

def test_report_of_a_missing_run(db, reports, capsys):
  report(99)
  assert "not found" in capsys.readouterr().out
  assert not reports.exists()

def test_report_write_errors_are_reported(db, scanner, workflows, answers, catalog, reports, capsys):
  fullRun(scanner, workflows, answers)
  reports.write_text("a file, not a folder", encoding="utf-8")
  report()
  assert "Could not write" in capsys.readouterr().out

HOSTILE = "evil\x1b[31m\n# Fake heading\n[click](http://evil.test) <img src=x onerror=alert(1)> ``` | `tick`"

def hostileRun(scanner, workflows, answers):
  host = FakeHost({80: {"state": "open", "name": "http", "product": HOSTILE, "version": HOSTILE, "script": {"http-title": HOSTILE}}}, hostname=HOSTILE)
  fullRun(scanner, workflows, answers, results={0: {"10.0.0.1": host}, 1: {"10.0.0.1": host}, 2: {"10.0.0.1": host}, 3: {"10.0.0.1": host}})

def test_markdown_report_keeps_hostile_data_inside_code(db, scanner, workflows, answers, catalog, reports):
  hostileRun(scanner, workflows, answers)
  report()
  text = (reports / "workflow-1.md").read_text(encoding="utf-8")
  assert "\x1b" not in text
  fenced = False
  fence = ""
  for line in text.splitlines():
    if fenced:
      fenced = line != fence
      continue
    if re.fullmatch(r"`{3,}", line):
      fenced, fence = True, line
      continue
    # Outside the output blocks, everything hostile is on one line, inside a code span
    assert not line.startswith("# Fake")
    assert not re.sub(r"(`+) .*? \1", "", line).count("evil")
  assert not fenced

def test_json_report_escapes_hostile_data_and_keeps_it(db, scanner, workflows, answers, catalog, reports):
  hostileRun(scanner, workflows, answers)
  report(extension="json")
  raw = (reports / "workflow-1.json").read_text(encoding="utf-8")
  assert "\x1b" not in raw
  assert json.loads(raw)["findings"][0]["output"] == HOSTILE

def test_report_of_a_run_from_an_earlier_version(db, scanner, workflows, answers, catalog, reports):
  fullRun(scanner, workflows, answers)
  connection = db.lite.connect(db.dbname)
  connection.execute("UPDATE workflow_stages SET definition=NULL, targets=NULL")
  connection.commit()
  connection.close()
  report()
  text = (reports / "workflow-1.md").read_text(encoding="utf-8")
  assert "Not recorded by the version" in text and "not recorded" in text

@pytest.mark.parametrize("value", ["not json", "[1, 2]", '{"source": "other"}', "3"])
def test_report_survives_damaged_stage_data(db, scanner, workflows, answers, catalog, reports, value):
  fullRun(scanner, workflows, answers)
  connection = db.lite.connect(db.dbname)
  connection.execute("UPDATE workflow_stages SET definition=?, targets=?", (value, value))
  connection.commit()
  connection.close()
  report()
  assert "Not recorded by the version" in (reports / "workflow-1.md").read_text(encoding="utf-8")

def test_targets_are_recorded_again_when_a_stage_resumes(db, scanner, workflows, answers, catalog):
  runId = savedRun(db, ["completed", "interrupted"], stages=CHAIN[:2], workflows=workflows)
  foundFirstStage(db, runId, ("10.0.0.1", "10.0.0.2"))
  answers.append("y")
  resume(runId)
  assert json.loads(db.getRun(runId)["stages"][1]["targets"]) == [{"target": "10.0.0.1", "ports": None}, {"target": "10.0.0.2", "ports": None}]

def test_older_databases_get_the_targets_column(db, scanner, workflows, answers, catalog):
  connection = db.lite.connect(db.dbname)
  db.getRuns()
  connection.executescript("""ALTER TABLE workflow_stages DROP COLUMN targets;
    INSERT INTO workflow_runs (workflow, target, status, started_at) VALUES ('w', '10.0.0.1', 'completed', 'x');
    INSERT INTO workflow_stages (run_id, position, name, arguments, status) VALUES (1, 0, 'a', '-sn', 'completed');""")
  connection.close()
  assert db.getRun(1)["stages"][0]["targets"] is None

# ---- Comparing runs

def compare(base=1, other=2):
  helperworkflow.HelperWorkflow("id:%d with:%d" % (base, other), "compare").process()

def twoRuns(scanner, workflows, answers, later, stages=CHAIN, secondName="w", secondNet="10.0.0.0/24"):
  fullRun(scanner, workflows, answers, stages=stages)
  fullRun(scanner, workflows, answers, stages=stages, results=later, name=secondName, net=secondNet)

def later(host, address="10.0.0.1"):
  return {0: {address: FakeHost({})}, 1: {address: host}, 2: {address: host}, 3: {address: host}}

def test_compare_finds_no_differences(db, scanner, workflows, answers, catalog, capsys):
  twoRuns(scanner, workflows, answers, later(HTTP_HOST["10.0.0.1"]))
  capsys.readouterr()
  compare()
  assert capsys.readouterr().out.strip() == "No differences between these runs"

def test_compare_shows_what_changed(db, scanner, workflows, answers, catalog, capsys):
  host = FakeHost({80: {"state": "open", "name": "http", "product": "nginx", "version": "2.0", "script": {"http-title": "Changed"}},
    443: {"state": "open", "name": "https", "script": {}}})
  twoRuns(scanner, workflows, answers, later(host))
  capsys.readouterr()
  compare()
  out = capsys.readouterr().out
  assert "[+] New open port: 10.0.0.1 443/tcp" in out
  assert "[~] Service changed: 10.0.0.1 80/tcp (http nginx 1.0 => http nginx 2.0)" in out
  assert "[~] Finding changed: 10.0.0.1 80 http-title (Welcome => Changed)" in out

def test_compare_shows_what_is_gone(db, scanner, workflows, answers, catalog, capsys):
  twoRuns(scanner, workflows, answers, later(FakeHost({22: {"state": "open", "name": "ssh"}}), "10.0.0.2"))
  capsys.readouterr()
  compare()
  out = capsys.readouterr().out
  assert "[-] Host no longer found: 10.0.0.1" in out and "[+] New host: 10.0.0.2" in out
  assert "[-] Port no longer open: 10.0.0.1 80/tcp" in out and "[-] Finding no longer present: 10.0.0.1 80 http-title" in out

def test_compare_warns_about_different_targets_and_workflows(db, scanner, workflows, answers, catalog, capsys):
  twoRuns(scanner, workflows, answers, later(HTTP_HOST["10.0.0.1"]), secondNet="10.0.0.1")
  capsys.readouterr()
  compare()
  assert "different workflow or target" in capsys.readouterr().out

def test_compare_does_not_warn_about_stages_with_nothing_to_scan(db, scanner, workflows, answers, catalog, capsys):
  twoRuns(scanner, workflows, answers, later(HTTP_HOST["10.0.0.1"]))
  db.setStageStatus(2, 3, "skipped")
  capsys.readouterr()
  compare()
  assert "did not finish" not in capsys.readouterr().out

@pytest.mark.parametrize("status,stageStatus", [("interrupted", "interrupted"), ("completed", "declined"), ("completed", "failed")])
def test_compare_warns_about_unfinished_runs(db, scanner, workflows, answers, catalog, capsys, status, stageStatus):
  twoRuns(scanner, workflows, answers, later(HTTP_HOST["10.0.0.1"]))
  db.setStageStatus(2, 3, stageStatus)
  db.setRunStatus(2, status)
  capsys.readouterr()
  compare()
  assert "did not finish every stage" in capsys.readouterr().out

def test_compare_sanitizes_remote_data(db, scanner, workflows, answers, catalog, capsys):
  host = FakeHost({80: {"state": "open", "name": "http", "product": "evil\x1b[31m", "script": {"bad\x1b[0m": "out\x1b[2J"}}})
  twoRuns(scanner, workflows, answers, later(host))
  capsys.readouterr()
  compare()
  assert "\x1b" not in capsys.readouterr().out

@pytest.mark.parametrize("args,message", [("", "help workflow"), ("id:1", "help workflow"), ("with:1", "help workflow"), ("id:x with:1", "help workflow"),
  ("id:1 with:\u00b2", "help workflow"), ("id:1 with:2 net:x", "help workflow"), ("id:1 with:2", "not found")])
def test_compare_rejects_bad_arguments(db, scanner, capsys, args, message):
  helperworkflow.HelperWorkflow(args, "compare").process()
  assert message in capsys.readouterr().out

def test_report_and_compare_never_scan(db, scanner, workflows, answers, catalog, reports):
  fullRun(scanner, workflows, answers)
  count = len(scanner.calls)
  report()
  compare(1, 1)
  assert len(scanner.calls) == count

@pytest.mark.parametrize("value,expected", [("a`b", "`` a`b ``"), ("a``b", "``` a``b ```"), ("`", "`` ` ``"), ("a\nb", "` a b `"), ("", "-"), (None, "-"), (80, "` 80 `")])
def test_code_spans_cannot_be_closed_by_their_content(value, expected):
  assert helperworkflow.mdCode(value) == expected

@pytest.mark.parametrize("output,fence", [("plain", "```"), ("x\n```\n# Fake", "````"), ("````", "`````")])
def test_output_blocks_cannot_be_closed_by_their_content(output, fence):
  assert helperworkflow.mdBlock(output) == fence + "\n" + output + "\n" + fence

def test_compare_treats_a_host_that_went_down_as_gone(db, scanner, workflows, answers, catalog, capsys):
  stages = CHAIN[:1]
  fullRun(scanner, workflows, answers, stages=stages, results={0: {"10.0.0.1": FakeHost({})}})
  fullRun(scanner, workflows, answers, stages=stages, results={0: {"10.0.0.1": FakeHost({}, state="down")}})
  capsys.readouterr()
  compare()
  assert "[-] Host no longer found: 10.0.0.1" in capsys.readouterr().out

# ---- Suggestions

def suggest(runId=1):
  helperworkflow.HelperWorkflow("id:" + str(runId), "suggest").process()

def foundRun(db, status="completed", ports=((80, "http"),), address="10.0.0.1"):
  runId = db.createRun("w", "10.0.0.0/24", [{"name": "discovery", "source": None, "services": None, "confirm": False, "arguments": "-sn"}])
  db.setStageStatus(runId, 0, "completed")
  db.saveStageResults(runId, "discovery", [{"address": address, "hostname": "", "state": "up"}],
    [{"address": address, "protocol": "tcp", "port": port, "state": "open", "service": service, "product": "", "version": ""} for port, service in ports], [])
  db.setRunStatus(runId, status)
  return runId

def test_suggestions_are_listed_and_nothing_runs_without_approval(db, scanner, catalog, answers, capsys):
  runId = foundRun(db)
  before = db.getRun(runId)
  answers.append("")
  suggest(runId)
  out = capsys.readouterr().out
  assert "1. http-headers" in out and "2. http-title" in out and "10.0.0.1:80" in out
  assert answers == [] and scanner.calls == []
  assert db.getRun(runId) == before

@pytest.mark.parametrize("answer", ["", "   ", "0", "3", "x", "1,", "1;2", "-1", "\u00b2", "1 2", "http-title", "99999", EOFError, KeyboardInterrupt])
def test_anything_but_a_valid_selection_runs_nothing(db, scanner, catalog, monkeypatch, answer):
  runId = foundRun(db)
  before = db.getRun(runId)
  # A later "y" must not rescue a selection that should have stopped everything
  given = [answer]
  def respond(message):
    value = given.pop(0) if given else "y"
    if isinstance(value, str):
      return value
    raise value
  monkeypatch.setattr("builtins.input", respond)
  suggest(runId)
  assert scanner.calls == []
  assert db.getRun(runId) == before

@pytest.mark.parametrize("answer", ["n", "", EOFError, KeyboardInterrupt])
def test_refusing_the_authorization_runs_nothing(db, scanner, catalog, monkeypatch, capsys, answer):
  runId = foundRun(db)
  before = db.getRun(runId)
  given = ["1", answer]
  def respond(message):
    value = given.pop(0)
    if isinstance(value, str):
      return value
    raise value
  monkeypatch.setattr("builtins.input", respond)
  suggest(runId)
  assert given == [] and scanner.calls == []
  assert db.getRun(runId) == before

@pytest.mark.parametrize("selection,expected", [("2", "http-title"), ("all", "http-headers or http-title"), ("2,1,2", "http-headers or http-title")])
def test_approved_scripts_run_only_on_the_ports_of_that_service(db, scanner, catalog, answers, selection, expected):
  runId = foundRun(db, ports=((80, "http"), (22, "ssh")))
  answers += [selection, "y", "", ]
  scanner.results = {0: {"10.0.0.1": FakeHost({80: {"state": "open", "name": "http", "script": {"http-title": "Hi"}}})}}
  suggest(runId)
  assert answers == []
  assert len(scanner.calls) == 1
  hosts, ports, arguments = scanner.calls[0]
  assert (hosts, ports) == ("10.0.0.1", "80")
  assert "(" + expected + ") and not (broadcast or dos)" in arguments and "--host-timeout" in arguments
  details = db.getRun(runId)
  assert details["run"]["status"] == "completed"
  assert details["stages"][1]["name"] == "suggested-2" and details["stages"][1]["status"] == "completed"
  assert details["findings"][0]["stage"] == "suggested-2" and details["findings"][0]["script"] == "http-title"

def test_only_safe_scripts_are_suggested(db, scanner, catalog, answers, capsys):
  runId = foundRun(db)
  answers.append("")
  suggest(runId)
  out = capsys.readouterr().out
  assert "http-sql" not in out and "http-slowloris" not in out and "bc" not in out

def test_broadcast_and_dos_scripts_are_never_suggested_even_if_safe(monkeypatch):
  monkeypatch.setitem(helperworkflow.SUGGESTIONS, "fake", ("x",))
  scripts = {"x-one": {"safe"}, "x-two": {"safe", "broadcast"}, "x-three": {"safe", "dos"}, "x-four": {"vuln"}, "xother": {"safe"}}
  assert helperworkflow.suggestedScripts("fake", scripts, set()) == ["x-one"]

def test_scripts_already_used_are_not_suggested_again(db, scanner, catalog, answers, capsys):
  runId = foundRun(db)
  answers += ["1", "y"]
  suggest(runId)
  capsys.readouterr()
  answers.append("")
  suggest(runId)
  out = capsys.readouterr().out
  assert "http-headers" not in out and "1. http-title" in out

def test_scripts_with_saved_results_are_not_suggested(db, scanner, catalog, answers, capsys):
  runId = foundRun(db)
  db.saveStageResults(runId, "discovery", [], [], [{"address": "10.0.0.1", "port": 80, "script": "http-title", "output": "Hi"}])
  answers.append("")
  suggest(runId)
  out = capsys.readouterr().out
  assert "http-title" not in out and "1. http-headers" in out

def test_nothing_left_to_suggest(db, scanner, catalog, answers, capsys):
  runId = foundRun(db)
  answers += ["all", "y"]
  suggest(runId)
  capsys.readouterr()
  calls = len(scanner.calls)
  suggest(runId)
  assert "No script suggestions" in capsys.readouterr().out
  assert len(scanner.calls) == calls and answers == []

@pytest.mark.parametrize("service", ["unknown", "http;rm -rf /", "--script=vuln", "http --script vuln", "HTTP", "http\x1b[31m", ""])
def test_services_outside_the_table_never_produce_suggestions(db, scanner, catalog, capsys, service):
  runId = foundRun(db, ports=((80, service),))
  suggest(runId)
  out = capsys.readouterr().out
  assert "No script suggestions" in out and "\x1b" not in out
  assert scanner.calls == []

def test_remote_data_never_reaches_the_nmap_arguments(db, scanner, catalog, answers):
  runId = foundRun(db)
  db.saveStageResults(runId, "discovery", [], [{"address": "10.0.0.1", "protocol": "tcp", "port": 80, "state": "open", "service": "http",
    "product": "--script=vuln", "version": "-oN /tmp/x"}], [{"address": "10.0.0.1", "port": 80, "script": "--script=vuln", "output": "-iL /tmp/x"}])
  answers += ["all", "y"]
  suggest(runId)
  hosts, ports, arguments = scanner.calls[0]
  assert "vuln" not in arguments and "/tmp" not in arguments and "-oN" not in arguments and "-iL" not in arguments

def test_suggestions_ignore_results_outside_the_scope(db, scanner, catalog, answers, capsys):
  runId = foundRun(db)
  answers += ["1", "y"]
  scanner.results = {0: {"8.8.8.8": FakeHost({80: {"state": "open", "name": "http"}})}}
  suggest(runId)
  assert "Ignored result" in capsys.readouterr().out
  assert [host["address"] for host in db.getRun(runId)["hosts"]] == ["10.0.0.1"]

@pytest.mark.parametrize("status", ["interrupted", "failed", "running"])
def test_suggestions_need_a_completed_run(db, scanner, catalog, capsys, status):
  runId = foundRun(db, status=status)
  before = db.getRun(runId)
  suggest(runId)
  assert "need a completed run" in capsys.readouterr().out
  assert scanner.calls == []
  assert db.getRun(runId) == before

@pytest.mark.parametrize("args,message", [("", "help workflow"), ("foo:1", "help workflow"), ("id:x", "help workflow"), ("id:\u00b2", "help workflow"),
  ("id:1 net:10.0.0.1", "help workflow"), ("id:99", "not found")])
def test_suggest_rejects_bad_arguments(db, scanner, capsys, args, message):
  helperworkflow.HelperWorkflow(args, "suggest").process()
  assert message in capsys.readouterr().out
  assert scanner.calls == []

@pytest.mark.parametrize("error,status", [(nmap.PortScannerError("boom"), "failed"), (KeyboardInterrupt(), "interrupted")])
def test_a_suggested_stage_that_stops_leaves_the_run_completed(db, scanner, catalog, answers, error, status):
  runId = foundRun(db)
  answers += ["1", "y"]
  scanner.error = (1, error)
  suggest(runId)
  details = db.getRun(runId)
  assert details["run"]["status"] == "completed"
  assert details["stages"][1]["status"] == status

def test_an_unfinished_suggestion_is_offered_again(db, scanner, catalog, answers, capsys):
  runId = foundRun(db)
  answers += ["1", "y"]
  scanner.error = (1, KeyboardInterrupt())
  suggest(runId)
  capsys.readouterr()
  scanner.error = None
  answers.append("")
  suggest(runId)
  assert "1. http-headers" in capsys.readouterr().out

def test_suggest_without_nmap_changes_nothing(db, catalog, answers, monkeypatch, capsys):
  def missing():
    raise nmap.PortScannerError("missing")
  monkeypatch.setattr(nmap, "PortScanner", missing)
  runId = foundRun(db)
  before = db.getRun(runId)
  answers += ["1", "y"]
  suggest(runId)
  assert "nmap" in capsys.readouterr().out.lower()
  assert db.getRun(runId) == before

def test_each_service_is_asked_separately(db, scanner, catalog, answers):
  runId = foundRun(db, ports=((80, "http"), (22, "ssh")))
  answers += ["", "1", "y"]
  suggest(runId)
  assert answers == []
  assert [(hosts, ports) for hosts, ports, _ in scanner.calls] == [("10.0.0.1", "22")]
  assert "ssh-hostkey" in scanner.calls[0][2]

def test_report_explains_a_suggested_stage(db, scanner, catalog, answers, reports):
  runId = foundRun(db)
  answers += ["1", "y"]
  suggest(runId)
  report(runId, "json")
  stage = json.loads((reports / ("workflow-%d.json" % runId)).read_text(encoding="utf-8"))["stages"][1]
  assert "approved by the operator" in stage["reason"] and "http" in stage["reason"]
  assert stage["targets"] == [{"target": "10.0.0.1", "ports": "80"}]

def test_every_service_in_the_table_has_real_safe_scripts():
  dbFile = "/opt/homebrew/share/nmap/scripts/script.db"
  if not os.path.isfile(dbFile):
    pytest.skip("nmap is not installed here")
  scripts = {}
  with open(dbFile, encoding="utf-8") as f:
    for name, found in re.findall(r'filename = "([^"]+)\.nse", categories = \{([^}]*)\}', f.read()):
      scripts[name] = set(re.findall(r'"([a-z]+)"', found))
  for service in helperworkflow.SUGGESTIONS:
    names = helperworkflow.suggestedScripts(service, scripts, set())
    assert names, service
    assert all("safe" in scripts[name] and not scripts[name] & {"dos", "broadcast"} for name in names)
    validateArguments("--script " + ",".join(names), "services", False, "15m", scripts)

# ---- Service names

def test_stages_that_depend_on_services_use_version_detection():
  assert "-sV" in shlex.split(args("--script http-title", "services"))
  assert shlex.split(args("-sV --script http-title", "services")).count("-sV") == 1
  assert "-sV" not in shlex.split(args("--top-ports 10", "live_hosts"))

def test_shipped_script_stages_detect_services(db):
  for name in ("web", "ssh", "smb"):
    loaded = helperworkflow.loadWorkflow(name, {script: {"safe"} for script in re.findall(r"[a-z0-9-]+", open(os.path.join(helperworkflow.WORKFLOWS_DIR, name + ".yaml"), encoding="utf-8").read())} | {"vuln": {"vuln"}})
    assert all("-sV" in shlex.split(stage["arguments"]) for stage in loaded if stage["source"] == "services")

def test_a_guessed_service_does_not_replace_a_detected_one(db, scanner, workflows, answers, catalog):
  detected = FakeHost({8080: {"state": "open", "name": "http", "product": "nginx", "conf": "10"}})
  guessed = FakeHost({8080: {"state": "open", "name": "http-proxy", "conf": "3"}})
  stages = CHAIN[:3] + [{"name": "first", "from": "open_ports", "arguments": "--version-intensity 0"}, {"name": "enum", "from": "services", "when": {"service": ["http"]}, "arguments": "--script http-title"}]
  answers.append("y")
  workflows("w", stages)
  scanner.results = {0: {"10.0.0.1": FakeHost({})}, 1: {"10.0.0.1": guessed}, 2: {"10.0.0.1": detected}, 3: {"10.0.0.1": guessed}, 4: {"10.0.0.1": detected}}
  helperworkflow.HelperWorkflow("name:w net:10.0.0.0/24", "run").process()
  details = db.getRun(1)
  assert details["services"][0]["service"] == "http" and details["services"][0]["product"] == "nginx"
  assert details["stages"][4]["status"] == "completed"
  assert scanner.calls[4][:2] == ("10.0.0.1", "8080")

def test_a_guess_is_kept_until_something_better_is_found(db):
  runId = foundRun(db, ports=())
  def save(name, guess):
    db.saveStageResults(runId, "x", [], [{"address": "10.0.0.1", "protocol": "tcp", "port": 8081, "state": "open", "service": name, "product": "", "version": "", "guess": guess}], [])
    return db.getRun(runId)["services"][0]["service"]
  assert save("blackice-icecap", True) == "blackice-icecap"
  assert save("other-guess", True) == "blackice-icecap"
  assert save("http", False) == "http"
  assert save("http-proxy", True) == "http"
  assert save("https", False) == "https"

def test_a_guess_fills_in_an_empty_service(db):
  runId = foundRun(db, ports=((8081, ""),))
  db.saveStageResults(runId, "x", [], [{"address": "10.0.0.1", "protocol": "tcp", "port": 8081, "state": "open", "service": "http-proxy", "product": "", "version": "", "guess": True}], [])
  assert db.getRun(runId)["services"][0]["service"] == "http-proxy"

# ---- Findings from the validation of the reports

def test_compare_warns_when_the_stages_differ(db, scanner, workflows, answers, catalog, capsys):
  fullRun(scanner, workflows, answers, stages=CHAIN[:2], results={0: {"10.0.0.1": FakeHost({})}, 1: HTTP_HOST})
  fullRun(scanner, workflows, answers, stages=CHAIN[:1], results={0: {"10.0.0.1": FakeHost({})}})
  capsys.readouterr()
  compare()
  out = capsys.readouterr().out
  assert "used different stages" in out and "Port no longer open" in out

def test_compare_warns_about_suggested_stages(db, scanner, workflows, answers, catalog, capsys):
  twoRuns(scanner, workflows, answers, later(HTTP_HOST["10.0.0.1"]))
  answers += ["1", "y"]
  suggest(2)
  capsys.readouterr()
  compare()
  assert "used different stages" in capsys.readouterr().out

def test_compare_does_not_warn_about_equal_stages(db, scanner, workflows, answers, catalog, capsys):
  twoRuns(scanner, workflows, answers, later(HTTP_HOST["10.0.0.1"]))
  capsys.readouterr()
  compare()
  assert "different stages" not in capsys.readouterr().out

@pytest.mark.skipif(os.name == "nt", reason="symlink permissions")
def test_report_rejects_a_symlinked_folder(db, scanner, workflows, answers, catalog, reports, tmp_path, capsys):
  fullRun(scanner, workflows, answers)
  outside = tmp_path / "outside"
  outside.mkdir()
  reports.symlink_to(outside)
  capsys.readouterr()
  report()
  assert "symbolic link" in capsys.readouterr().out
  assert os.listdir(outside) == []

@pytest.mark.parametrize("character", ["\u202e", "\u2066", "\u200f", "\u2028", "\u2029"])
def test_direction_and_line_controls_are_neutralized(character):
  assert character not in helperworkflow.mdCode("a" + character + "b")
  assert character not in helperworkflow.mdBlock("a" + character + "b")
  assert character not in helperworkflow.sanitize("a" + character + "b")

@pytest.mark.parametrize("error", [KeyboardInterrupt, OSError])
def test_no_temporary_file_is_left_behind(db, scanner, workflows, answers, catalog, reports, monkeypatch, error):
  fullRun(scanner, workflows, answers)
  def fail(source, target):
    raise error("stop")
  monkeypatch.setattr(helperworkflow.os, "replace", fail)
  with pytest.raises(error):
    helperworkflow.writeReport(1, "md", "content")
  assert os.listdir(reports) == []

@pytest.mark.parametrize("definition", ['{"source": "services", "services": "ssh"}', '{"source": "services", "services": 3}', '{"source": "suggestion", "services": "ssh"}'])
def test_badly_typed_definitions_give_no_reason(definition):
  assert "Not recorded" in helperworkflow.stageReason({"definition": definition, "status": "completed"})

@pytest.mark.parametrize("services", ["null", "[]"])
def test_all_services_reason(services):
  assert "the services found" in helperworkflow.stageReason({"definition": '{"source": "services", "services": ' + services + "}", "status": "completed"})

@pytest.mark.parametrize("status,unfinished", [("failed", True), ("interrupted", True), ("running", True), ("completed", False), ("pending", False)])
def test_report_says_when_a_stage_did_not_finish(status, unfinished):
  reason = helperworkflow.stageReason({"definition": '{"source": "live_hosts", "confirm": true}', "status": status})
  assert ("It did not finish" in reason) == unfinished

def test_findings_are_found_by_run_without_a_full_scan(db):
  db.getRuns()
  connection = db.lite.connect(db.dbname)
  plan = " ".join(str(row[3]) for row in connection.execute("EXPLAIN QUERY PLAN SELECT * FROM workflow_findings WHERE run_id=1 ORDER BY id"))
  connection.close()
  assert "workflow_findings_run" in plan
