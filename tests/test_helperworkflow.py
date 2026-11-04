import nmap
import pytest
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

def test_smb_only_uses_safe_scripts_for_smb_services():
  with open(helperworkflow.os.path.join(helperworkflow.BASE_DIR, "workflows", "smb.yaml"), encoding="utf-8") as f:
    content = yaml.safe_load(f)
  stages = content["smb"]["stages"]
  assert not any(stage.get("confirm") for stage in stages)
  assert stages[-1]["when"] == {"service": ["microsoft-ds", "netbios-ssn"]}
  categories = dict(SCRIPTS)
  for script in stages[-1]["arguments"].split()[1].split(","):
    categories[script] = {"safe"}
  validateWorkflow("smb", content, categories)

def test_resume_messages_exist_in_every_language():
  for language in ("en", "es"):
    with open(helperworkflow.os.path.join(helperworkflow.BASE_DIR, "i18n", "help." + language + ".yml"), encoding="utf-8") as f:
      messages = yaml.safe_load(f)[language]
    for key in ("workflow_not_resumable", "workflow_changed", "workflow_resume_nothing", "workflow_resume_hint"):
      assert messages[key]

def test_a_resumed_run_is_running_while_it_scans(db, scanner, workflows, answers, catalog, monkeypatch):
  runId = savedRun(db, ["completed", "interrupted"], stages=CHAIN[:2], workflows=workflows)
  foundFirstStage(db, runId)
  seen = []
  monkeypatch.setattr(scanner, "scan", lambda hosts, ports=None, arguments="": seen.append(db.getRun(runId)["run"]))
  answers.append("y")
  resume(runId)
  assert seen[0]["status"] == "running" and seen[0]["finished_at"] is None
