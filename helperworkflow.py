import fnmatch
import i18n
import ipaddress
import json
import nmap
import os
import re
import shlex
import tempfile
import yaml

import dbmodule

from dbmodule import BASE_DIR
from helper import isValidTarget, parseArgs, sanitize

WORKFLOWS_DIR = os.path.join(BASE_DIR, "workflows")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
HOST_TIMEOUT = "15m"
STAGE_KEYS = {"name", "from", "when", "confirm", "arguments", "host_timeout"}
SOURCES = {"live_hosts", "open_ports", "services"}
FLAGS = {"-sn", "-sT", "-sS", "-sV", "-Pn", "-n", "-v", "-vv", "-F", "-O", "-T0", "-T1", "-T2", "-T3", "-T4", "-T5", "--open", "--reason"}
VALUES = {"--script", "--script-args", "--script-timeout", "--top-ports", "-p", "--host-timeout", "--max-retries", "--min-rate", "--max-rate", "--version-intensity"}
PORT_OPTIONS = {"-p", "--top-ports", "-F"}
VALUE_RE = r"[A-Za-z0-9._,:=/-]+"
# These never run: dos can take targets down, and broadcast reaches hosts outside the scope
BLOCKED_SCRIPTS = {"dos", "broadcast"}
RESUMABLE_RUNS = ("interrupted", "failed", "running")
FINISHED_STAGES = ("completed", "skipped", "declined")
# Script name prefixes per service. A service name comes from the scanned host, so it is only ever
# looked up here, and what reaches nmap comes from this table and the script database
SUGGESTIONS = {
  "http": ("http",), "http-alt": ("http",), "http-proxy": ("http",), "https": ("http", "ssl"),
  "ssh": ("ssh", "ssh2"), "ftp": ("ftp",), "smtp": ("smtp",), "domain": ("dns",),
  "microsoft-ds": ("smb", "smb2"), "netbios-ssn": ("smb", "smb2", "nbstat"),
  "mysql": ("mysql",), "ms-sql-s": ("ms-sql",), "ms-wbt-server": ("rdp",), "imap": ("imap",), "pop3": ("pop3",),
  "ldap": ("ldap",), "telnet": ("telnet",), "vnc": ("vnc",), "redis": ("redis",), "mongodb": ("mongodb",),
}

class WorkflowError(Exception):
  pass

def __scriptMatches(token, scripts):
  name = re.sub(r"\.nse$", "", token)
  matches = {script: found for script, found in scripts.items() if fnmatch.fnmatchcase(script, name) or token in found}
  if not matches:
    raise WorkflowError("unknown script or category: " + token)
  return matches

# Returns the script expression that nmap will receive
def __validateScripts(expression, confirm, scripts):
  normalized = expression.replace(",", " or ")
  needsConfirm = False
  depth = 0
  for token in re.findall(r"[()]|[^\s()]+", normalized):
    if token == "(":
      depth += 1
      continue
    if token == ")":
      depth -= 1
      # An unbalanced expression could escape the exclusions added below
      if depth < 0:
        raise WorkflowError("unbalanced parentheses: " + expression)
      continue
    if token in ("and", "or"):
      continue
    if token == "not":
      needsConfirm = True
      continue
    if not re.fullmatch(r"[A-Za-z0-9_.*-]+", token):
      raise WorkflowError("invalid script name: " + token)
    if token in BLOCKED_SCRIPTS:
      raise WorkflowError("script category not allowed: " + token)
    matches = __scriptMatches(token, scripts)
    name = re.sub(r"\.nse$", "", token)
    if name in matches and matches[name] & BLOCKED_SCRIPTS:
      raise WorkflowError("script not allowed: " + token)
    if any("safe" not in found for found in matches.values()):
      needsConfirm = True
  if depth != 0:
    raise WorkflowError("unbalanced parentheses: " + expression)
  if needsConfirm and not confirm:
    raise WorkflowError("these scripts require confirm: true: " + expression)
  return "(" + normalized + ") and not (" + " or ".join(sorted(BLOCKED_SCRIPTS)) + ")"

# Only known options are accepted, so a template cannot add targets or read and write files
def validateArguments(arguments, source, confirm, hostTimeout, scripts):
  try:
    tokens = shlex.split(arguments)
  except ValueError:
    raise WorkflowError("invalid arguments: " + arguments)
  result = []
  values = {}
  index = 0
  while index < len(tokens):
    option, sep, value = tokens[index].partition("=")
    index += 1
    if option in FLAGS and not sep:
      result.append(option)
      values[option] = True
      continue
    if option not in VALUES:
      raise WorkflowError("option not allowed: " + tokens[index - 1])
    if not sep:
      if index == len(tokens):
        raise WorkflowError("missing value for: " + option)
      value = tokens[index]
      index += 1
    if option == "--script":
      value = __validateScripts(value, confirm, scripts)
    elif not re.fullmatch(VALUE_RE, value):
      raise WorkflowError("invalid value for " + option + ": " + value)
    if option == "--script-args" and (not confirm or "newtargets" in value):
      raise WorkflowError("--script-args requires confirm: true and cannot add targets")
    result += [option, value]
    values[option] = value
  if source in ("open_ports", "services") and PORT_OPTIONS & set(values):
    raise WorkflowError("this stage only scans the ports found earlier: " + arguments)
  if "--host-timeout" not in values:
    result += ["--host-timeout", hostTimeout]
  return shlex.join(result)

def validateWorkflow(name, content, scripts):
  if not isinstance(content, dict) or not isinstance(content.get(name), dict) or not isinstance(content[name].get("stages"), list) or not content[name]["stages"]:
    raise WorkflowError("the workflow needs a list of stages")
  stages = []
  names = set()
  for position, stage in enumerate(content[name]["stages"]):
    if not isinstance(stage, dict) or set(stage) - STAGE_KEYS or not isinstance(stage.get("name"), str) or not isinstance(stage.get("arguments"), str):
      raise WorkflowError("invalid stage: " + str(position + 1))
    if not re.fullmatch(r"[A-Za-z0-9_-]+", stage["name"]) or stage["name"] in names:
      raise WorkflowError("invalid or repeated stage name: " + stage["name"])
    names.add(stage["name"])
    source = stage.get("from")
    if (position == 0) != (source is None) or (source is not None and source not in SOURCES):
      raise WorkflowError("the first stage has no from, and the others use: " + ", ".join(sorted(SOURCES)))
    when = stage.get("when")
    services = None
    if when is not None:
      if source != "services" or not isinstance(when, dict) or set(when) != {"service"} or not isinstance(when["service"], list):
        raise WorkflowError("when needs from: services and a list of services: " + stage["name"])
      services = [str(service) for service in when["service"]]
    hostTimeout = str(stage.get("host_timeout", HOST_TIMEOUT))
    if not re.fullmatch(r"[0-9]+(ms|s|m|h)?", hostTimeout):
      raise WorkflowError("invalid host_timeout: " + hostTimeout)
    confirm = stage.get("confirm", False) is True
    stages.append({"name": stage["name"], "source": source, "services": services, "confirm": confirm,
      "arguments": validateArguments(stage["arguments"], source, confirm, hostTimeout, scripts)})
  return stages

def loadWorkflow(name, scripts):
  if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
    raise WorkflowError("invalid workflow name: " + name)
  try:
    with open(os.path.join(WORKFLOWS_DIR, name + ".yaml"), 'r', encoding="utf-8") as stream:
      return validateWorkflow(name, yaml.safe_load(stream), scripts)
  except (OSError, yaml.YAMLError) as e:
    raise WorkflowError("could not read the workflow: " + str(e))

def validAddress(address):
  try:
    return str(ipaddress.ip_address(address))
  except ValueError:
    return None

def validRunId(value):
  return re.fullmatch(r"[0-9]{1,18}", value) is not None

def askConfirmation(message):
  try:
    return input(message + " [y/N] ").strip().lower() in ("y", "yes", "s", "si", "sí")
  except (EOFError, KeyboardInterrupt):
    return False

# Convert the python-nmap result, ignoring anything outside the scope of the run
def collectResults(nm, scope):
  hosts, services, findings = [], [], []
  for host in nm.all_hosts():
    address = validAddress(host)
    if address is None or (scope is not None and address not in scope):
      print(i18n.t("help.workflow_out_of_scope") + ": " + sanitize(host))
      continue
    data = nm[host]
    hosts.append({"address": address, "hostname": data.hostname(), "state": data.state()})
    for script in data.get("hostscript", []):
      findings.append({"address": address, "port": None, "script": script.get("id", ""), "output": script.get("output", "")})
    for proto in data.all_protocols():
      for port in data[proto].keys():
        info = data[proto][port]
        services.append({"address": address, "protocol": proto, "port": int(port), "state": info.get("state", ""),
          "service": info.get("name", ""), "product": info.get("product", ""), "version": info.get("version", "")})
        for script, output in info.get("script", {}).items():
          findings.append({"address": address, "port": int(port), "script": script, "output": output})
  return hosts, services, findings

# Build the nmap calls of a stage, using only data from earlier stages of this run
def stageTargets(runId, stage, net):
  if stage["source"] is None:
    return [(net, None)]
  if stage["source"] == "live_hosts":
    hosts = [address for address in dbmodule.getLiveHosts(runId) if validAddress(address)]
    return [(address, None) for address in hosts]
  ports = dbmodule.getOpenPorts(runId, stage["services"])
  return [(address, ",".join(str(int(port)) for port in found)) for address, found in ports.items() if validAddress(address)]

def loadStored(value):
  try:
    return json.loads(value)
  except (TypeError, ValueError):
    return None

# Explain why a stage ran, from what the run saved when it started
def stageReason(stage):
  definition = loadStored(stage["definition"])
  if not isinstance(definition, dict) or "source" not in definition:
    return i18n.t("help.report_reason_unknown")
  source = definition["source"]
  services = definition.get("services")
  if source is None:
    reason = i18n.t("help.report_reason_first")
  elif source == "live_hosts":
    reason = i18n.t("help.report_reason_live_hosts")
  elif source == "open_ports":
    reason = i18n.t("help.report_reason_open_ports")
  elif source == "services" and isinstance(services, list) and services:
    reason = i18n.t("help.report_reason_services") + ": " + ", ".join(str(service) for service in services)
  elif source == "services":
    reason = i18n.t("help.report_reason_all_services")
  elif source == "suggestion" and isinstance(services, list):
    reason = i18n.t("help.report_reason_suggestion") + ": " + ", ".join(str(service) for service in services)
  else:
    return i18n.t("help.report_reason_unknown")
  if stage["status"] == "skipped":
    return reason + ". " + i18n.t("help.report_skipped")
  if stage["status"] == "declined":
    return reason + ". " + i18n.t("help.report_declined")
  if definition.get("confirm") is True and stage["status"] in ("completed", "failed", "interrupted"):
    return reason + ". " + i18n.t("help.report_confirmed")
  return reason

def stageReportTargets(stage):
  targets = loadStored(stage["targets"])
  if not isinstance(targets, list) or not all(isinstance(target, dict) for target in targets):
    return None
  return [{"target": target.get("target"), "ports": target.get("ports")} for target in targets]

def buildReport(details):
  run = details["run"]
  return {
    "run": {key: run[key] for key in ("id", "workflow", "target", "status", "started_at", "finished_at")},
    "stages": [{"position": stage["position"] + 1, "name": stage["name"], "status": stage["status"], "arguments": stage["arguments"],
      "reason": stageReason(stage), "targets": stageReportTargets(stage)} for stage in details["stages"]],
    "hosts": [{key: host[key] for key in ("address", "hostname", "state")} for host in details["hosts"]],
    "services": [{key: item[key] for key in ("address", "protocol", "port", "service", "product", "version")} for item in details["services"]],
    "findings": [{key: item[key] for key in ("stage", "address", "port", "script", "output")} for item in details["findings"]],
  }

def longestBackticks(text):
  return max((len(run) for run in re.findall(r"`+", text)), default=0)

# Data from scanned hosts only reaches a report inside code, so it cannot add links, HTML or headings
def mdCode(value):
  text = " ".join(sanitize("" if value is None else value).split())
  if not text:
    return "-"
  fence = "`" * (longestBackticks(text) + 1)
  return fence + " " + text + " " + fence

def mdBlock(value):
  text = sanitize(value)
  fence = "`" * max(3, longestBackticks(text) + 1)
  return fence + "\n" + text + "\n" + fence

def mdText(value):
  return re.sub(r"([\\`*_{}\[\]()<>#!|~&])", r"\\\1", " ".join(sanitize(value).split()))

def reportMarkdown(report):
  run = report["run"]
  lines = ["# " + i18n.t("help.report_title") + " " + str(run["id"]), ""]
  for label, key in (("report_workflow", "workflow"), ("report_target", "target"), ("report_status", "status"), ("report_started", "started_at"), ("report_finished", "finished_at")):
    lines.append("- " + i18n.t("help." + label) + ": " + mdCode(run[key]))
  lines += ["", "## " + i18n.t("help.report_stages"), ""]
  for stage in report["stages"]:
    lines += ["### " + str(stage["position"]) + ". " + mdCode(stage["name"]) + " " + mdCode(stage["status"]), "",
      "- " + i18n.t("help.report_reason") + ": " + mdText(stage["reason"]),
      "- " + i18n.t("help.report_arguments") + ": " + mdCode(stage["arguments"])]
    if stage["targets"] is None:
      lines.append("- " + i18n.t("help.report_targets") + ": " + i18n.t("help.report_not_recorded"))
    elif not stage["targets"]:
      lines.append("- " + i18n.t("help.report_targets") + ": " + i18n.t("help.report_none"))
    else:
      lines.append("- " + i18n.t("help.report_targets") + ":")
      for target in stage["targets"]:
        ports = " " + i18n.t("help.report_ports") + " " + mdCode(target["ports"]) if target["ports"] else ""
        lines.append("  - " + mdCode(target["target"]) + ports)
    lines.append("")
  lines += ["## " + i18n.t("help.report_hosts"), ""]
  lines += ["- " + mdCode(host["address"]) + " " + mdCode(host["hostname"]) + " " + mdCode(host["state"]) for host in report["hosts"]] or [i18n.t("help.report_none")]
  lines += ["", "## " + i18n.t("help.report_services"), ""]
  lines += ["- " + mdCode(item["address"]) + " " + mdCode(str(item["port"]) + "/" + str(item["protocol"])) + " " + mdCode(item["service"]) + " " + mdCode(item["product"]) + " " + mdCode(item["version"])
    for item in report["services"]] or [i18n.t("help.report_none")]
  lines += ["", "## " + i18n.t("help.report_findings"), ""]
  if not report["findings"]:
    lines.append(i18n.t("help.report_none"))
  for item in report["findings"]:
    lines += ["### " + mdCode(item["stage"]) + " " + mdCode(item["address"]) + " " + mdCode(item["port"]) + " " + mdCode(item["script"]), "", mdBlock(item["output"]), ""]
  return "\n".join(lines).rstrip() + "\n"

# The name is built from the run id, and only this user can read the file. A temporary file
# means a symlink left at the final path is replaced, not followed
def writeReport(runId, extension, content):
  os.makedirs(REPORTS_DIR, mode=0o700, exist_ok=True)
  path = os.path.join(REPORTS_DIR, "workflow-" + str(runId) + "." + extension)
  fd, tmppath = tempfile.mkstemp(dir=REPORTS_DIR)
  try:
    with os.fdopen(fd, 'w', encoding="utf-8") as f:
      f.write(content)
    os.replace(tmppath, path)
  except Exception:
    os.remove(tmppath)
    raise
  return path

def compareRuns(base, other):
  changes = []
  def compare(kind, before, after):
    for key in sorted(set(after) - set(before), key=str):
      changes.append(("+", "new_" + kind, key, None))
    for key in sorted(set(before) - set(after), key=str):
      changes.append(("-", "gone_" + kind, key, None))
    for key in sorted(set(before) & set(after), key=str):
      if before[key] != after[key]:
        changes.append(("~", "changed_" + kind, key, (before[key], after[key])))
  def hosts(details):
    return {(host["address"],): "" for host in details["hosts"] if host["state"] == "up"}
  def services(details):
    return {(item["address"], str(item["port"]) + "/" + item["protocol"]): " ".join(str(item[field] or "") for field in ("service", "product", "version")).strip() for item in details["services"]}
  def findings(details):
    return {(item["address"], str(item["port"] or "-"), item["script"]): item["output"] for item in details["findings"]}
  for kind, read in (("host", hosts), ("service", services), ("finding", findings)):
    compare(kind, read(base), read(other))
  return changes

# Scripts already run or tried in this run are not suggested again
def usedScripts(details):
  used = {item["script"] for item in details["findings"]}
  for stage in details["stages"]:
    if stage["status"] == "completed":
      used.update(re.findall(r"[A-Za-z0-9_.-]+", stage["arguments"]))
  return used

# Only scripts that a stage can run without confirm: safe ones, and never the blocked categories
def suggestedScripts(service, scripts, used):
  prefixes = SUGGESTIONS[service]
  return sorted(script for script, found in scripts.items() if "safe" in found and not found & BLOCKED_SCRIPTS and script not in used
    and any(script == prefix or script.startswith(prefix + "-") for prefix in prefixes))

# Anything but a valid list selects nothing
def askSelection(message, names):
  try:
    answer = input(message + ": ").strip().lower()
  except (EOFError, KeyboardInterrupt):
    return []
  if not answer:
    return []
  if answer == "all":
    return names
  chosen = [item.strip() for item in answer.split(",")]
  if not all(re.fullmatch(r"[0-9]{1,4}", item) and 1 <= int(item) <= len(names) for item in chosen):
    print(i18n.t("help.workflow_suggest_bad_selection"))
    return []
  return [names[index] for index in sorted({int(item) - 1 for item in chosen})]

class HelperWorkflow:

  def __init__(self, args="", command=""):
    self.args = args
    self.command = command

  def process(self):
    if self.command == "list":
      self.__list()
    elif self.command == "run":
      self.__run()
    elif self.command == "status":
      self.__status()
    elif self.command == "resume":
      self.__resume()
    elif self.command == "report":
      self.__report()
    elif self.command == "compare":
      self.__compare()
    elif self.command == "suggest":
      self.__suggest()
    else:
      print(i18n.t("help.workflow_error"))

  def __list(self):
    names = []
    if os.path.isdir(WORKFLOWS_DIR):
      names = sorted(name[:-5] for name in os.listdir(WORKFLOWS_DIR) if name.endswith(".yaml"))
    for name in names:
      print("[+] " + sanitize(name))

  def __run(self):
    params = parseArgs(self.args, ("name", "net"))
    if not params or set(params) != {"name", "net"}:
      print(i18n.t("help.workflow_error"))
      return
    if not isValidTarget(params["net"]):
      print(i18n.t("help.help_run_bad_target"))
      return
    try:
      stages = loadWorkflow(params["name"], dbmodule.scriptCategories())
    except WorkflowError as e:
      print(i18n.t("help.workflow_invalid") + ": " + sanitize(e))
      return
    self.__printPlan(params["net"], list(enumerate(stages)))
    if not askConfirmation(i18n.t("help.workflow_authorized")):
      print(i18n.t("help.workflow_cancelled"))
      return
    self.__execute(params["name"], params["net"], stages)

  def __printPlan(self, net, stages):
    print(i18n.t("help.workflow_plan") + ": " + sanitize(net))
    for position, stage in stages:
      print("  %d. %s: %s%s" % (position + 1, stage["name"], stage["arguments"], " (confirm)" if stage["confirm"] else ""))

  def __execute(self, name, net, stages, runId=None, finished=(), status=None):
    try:
      nm = nmap.PortScanner()
    except nmap.PortScannerError:
      print(i18n.t("help.help_run_nmap_missing"))
      return
    if runId is None:
      runId = dbmodule.createRun(name, net, stages)
    elif not dbmodule.claimRun(runId, status):
      print(i18n.t("help.workflow_already_resumed"))
      return
    print(i18n.t("help.workflow_started") + ": " + str(runId))
    scope = None
    for position, stage in enumerate(stages):
      if position in finished:
        continue
      # Later stages can only touch the hosts found by the first one
      if position > 0 and scope is None:
        scope = set(dbmodule.getLiveHosts(runId))
      label = "[%d/%d] %s" % (position + 1, len(stages), stage["name"])
      targets = stageTargets(runId, stage, net)
      dbmodule.setStageTargets(runId, position, targets)
      if not targets:
        dbmodule.setStageStatus(runId, position, "skipped")
        print(label + ": " + i18n.t("help.workflow_no_targets"))
        continue
      if stage["confirm"] and not askConfirmation(label + ": " + i18n.t("help.workflow_confirm_stage") + " " + sanitize(", ".join(target for target, _ in targets))):
        dbmodule.setStageStatus(runId, position, "declined")
        print(label + ": " + i18n.t("help.workflow_declined"))
        continue
      problem = self.__scanStage(nm, runId, position, stage, targets, scope, label)
      if problem:
        dbmodule.setRunStatus(runId, problem)
        print(i18n.t("help.workflow_resume_hint") + ": workflow resume id:" + str(runId))
        return
    dbmodule.setRunStatus(runId, "completed")
    self.__printRun(dbmodule.getRun(runId))

  # Returns the status of the stage if it could not finish
  def __scanStage(self, nm, runId, position, stage, targets, scope, label):
    print(label + ": " + i18n.t("help.running_scan"))
    dbmodule.setStageStatus(runId, position, "running")
    try:
      for target, ports in targets:
        arguments = ("-6 " if ":" in target else "") + stage["arguments"]
        nm.scan(hosts=target, ports=ports, arguments=arguments)
        dbmodule.saveStageResults(runId, stage["name"], *collectResults(nm, scope))
    except (nmap.PortScannerError, OSError, dbmodule.lite.Error) as e:
      dbmodule.setStageStatus(runId, position, "failed")
      print(label + ": " + i18n.t("help.help_run_scan_error") + ": " + sanitize(e))
      return "failed"
    except KeyboardInterrupt:
      dbmodule.setStageStatus(runId, position, "interrupted")
      print(label + ": " + i18n.t("help.help_run_interrupted"))
      return "interrupted"
    dbmodule.setStageStatus(runId, position, "completed")
    return None

  def __status(self):
    params = parseArgs(self.args, ("id",))
    if params is None or ("id" in params and not validRunId(params["id"])):
      print(i18n.t("help.workflow_error"))
      return
    if params:
      details = dbmodule.getRun(int(params["id"]))
      if details is None:
        print(i18n.t("help.workflow_not_found"))
      else:
        self.__printRun(details)
      return
    for run in dbmodule.getRuns():
      print("[%d] %s %s %s %s" % (run["id"], sanitize(run["workflow"]), sanitize(run["target"]), sanitize(run["status"]), sanitize(run["started_at"])))

  def __resume(self):
    params = parseArgs(self.args, ("id",))
    if not params or not validRunId(params["id"]):
      print(i18n.t("help.workflow_error"))
      return
    runId = int(params["id"])
    details = dbmodule.getRun(runId)
    if details is None:
      print(i18n.t("help.workflow_not_found"))
      return
    if details["run"]["status"] not in RESUMABLE_RUNS:
      print(i18n.t("help.workflow_not_resumable") + ": " + sanitize(details["run"]["status"]))
      return
    net = details["run"]["target"]
    if not isValidTarget(net):
      print(i18n.t("help.help_run_bad_target"))
      return
    name = details["run"]["workflow"]
    try:
      stages = loadWorkflow(name, dbmodule.scriptCategories())
    except WorkflowError as e:
      print(i18n.t("help.workflow_invalid") + ": " + sanitize(e))
      return
    # The confirmation given for this run only covers the stages it started with
    if [dbmodule.stageDefinition(stage) for stage in stages] != [stage["definition"] for stage in details["stages"]]:
      print(i18n.t("help.workflow_changed"))
      return
    finished = {stage["position"] for stage in details["stages"] if stage["status"] in FINISHED_STAGES}
    remaining = [(position, stage) for position, stage in enumerate(stages) if position not in finished]
    if not remaining:
      dbmodule.setRunStatus(runId, "completed")
      print(i18n.t("help.workflow_resume_nothing"))
      self.__printRun(dbmodule.getRun(runId))
      return
    self.__printPlan(net, remaining)
    status = details["run"]["status"]
    if status == "running":
      print(i18n.t("help.workflow_resume_running"))
    if not askConfirmation(i18n.t("help.workflow_authorized")):
      print(i18n.t("help.workflow_cancelled"))
      return
    self.__execute(name, net, stages, runId, finished, status)

  def __report(self):
    params = parseArgs(self.args, ("id", "format"))
    if not params or "id" not in params or not validRunId(params["id"]) or params.get("format", "md") not in ("md", "json"):
      print(i18n.t("help.workflow_error"))
      return
    details = dbmodule.getRun(int(params["id"]))
    if details is None:
      print(i18n.t("help.workflow_not_found"))
      return
    report = buildReport(details)
    extension = params.get("format", "md")
    # JSON keeps the output as it was received, with anything unusual escaped
    content = reportMarkdown(report) if extension == "md" else json.dumps(report, indent=2) + "\n"
    try:
      path = writeReport(details["run"]["id"], extension, content)
    except OSError as e:
      print(i18n.t("help.workflow_report_error") + ": " + sanitize(e))
      return
    print(i18n.t("help.workflow_report_saved") + ": " + sanitize(path))

  def __compare(self):
    params = parseArgs(self.args, ("id", "with"))
    if not params or set(params) != {"id", "with"} or not validRunId(params["id"]) or not validRunId(params["with"]):
      print(i18n.t("help.workflow_error"))
      return
    base = dbmodule.getRun(int(params["id"]))
    other = dbmodule.getRun(int(params["with"]))
    if base is None or other is None:
      print(i18n.t("help.workflow_not_found"))
      return
    # A missing host or port means nothing if that run did not scan the same thing
    if base["run"]["workflow"] != other["run"]["workflow"] or base["run"]["target"] != other["run"]["target"]:
      print(i18n.t("help.workflow_compare_different"))
    if any(details["run"]["status"] != "completed" or any(stage["status"] != "completed" for stage in details["stages"]) for details in (base, other)):
      print(i18n.t("help.workflow_compare_incomplete"))
    changes = compareRuns(base, other)
    if not changes:
      print(i18n.t("help.workflow_compare_same"))
    for sign, label, key, values in changes:
      print("[%s] %s: %s%s" % (sign, i18n.t("help.compare_" + label), sanitize(" ".join(key)), " (" + sanitize(values[0]) + " => " + sanitize(values[1]) + ")" if values else ""))

  def __suggest(self):
    params = parseArgs(self.args, ("id",))
    if not params or not validRunId(params["id"]):
      print(i18n.t("help.workflow_error"))
      return
    runId = int(params["id"])
    details = dbmodule.getRun(runId)
    if details is None:
      print(i18n.t("help.workflow_not_found"))
      return
    # Stages added to an unfinished run would stop it from being resumed
    if details["run"]["status"] != "completed":
      print(i18n.t("help.workflow_suggest_not_completed") + ": " + sanitize(details["run"]["status"]))
      return
    scripts = dbmodule.scriptCategories()
    used = usedScripts(details)
    groups = [(service, suggestedScripts(service, scripts, used)) for service in sorted({item["service"] for item in details["services"]} & set(SUGGESTIONS))]
    groups = [(service, names) for service, names in groups if names]
    if not groups:
      print(i18n.t("help.workflow_suggest_none"))
      return
    scope = set(dbmodule.getLiveHosts(runId))
    scanned = False
    for service, names in groups:
      targets = stageTargets(runId, {"source": "services", "services": [service]}, None)
      if not targets:
        continue
      places = sanitize(", ".join(target + ":" + ports for target, ports in targets))
      print("[+] " + service + ": " + places)
      for number, name in enumerate(names, 1):
        print("  %d. %s" % (number, sanitize(name)))
      selected = askSelection(i18n.t("help.workflow_suggest_select"), names)
      if not selected:
        continue
      try:
        arguments = validateArguments("--script " + ",".join(selected), "services", False, HOST_TIMEOUT, scripts)
      except WorkflowError as e:
        print(i18n.t("help.workflow_invalid") + ": " + sanitize(e))
        continue
      print(i18n.t("help.workflow_plan") + ": " + places)
      print("  " + sanitize(arguments))
      if not askConfirmation(i18n.t("help.workflow_authorized")):
        print(i18n.t("help.workflow_cancelled"))
        continue
      try:
        nm = nmap.PortScanner()
      except nmap.PortScannerError:
        print(i18n.t("help.help_run_nmap_missing"))
        return
      position, stage = dbmodule.addStage(runId, "suggested", {"source": "suggestion", "services": [service], "confirm": False, "arguments": arguments})
      dbmodule.setStageTargets(runId, position, targets)
      if self.__scanStage(nm, runId, position, stage, targets, scope, "[" + stage["name"] + "]"):
        return
      scanned = True
    if scanned:
      self.__printRun(dbmodule.getRun(runId))

  def __printRun(self, details):
    run = details["run"]
    print("[%d] %s %s: %s" % (run["id"], sanitize(run["workflow"]), sanitize(run["target"]), sanitize(run["status"])))
    for stage in details["stages"]:
      print("  %s: %s" % (sanitize(stage["name"]), sanitize(stage["status"])))
    for host in details["hosts"]:
      print("Host : %s (%s) %s" % (sanitize(host["address"]), sanitize(host["hostname"] or ""), sanitize(host["state"])))
    for item in details["services"]:
      print("  %s %d/%s %s %s %s" % (sanitize(item["address"]), item["port"], sanitize(item["protocol"]), sanitize(item["service"] or ""), sanitize(item["product"] or ""), sanitize(item["version"] or "")))
    for item in details["findings"]:
      print("  [%s] %s:%s %s => %s" % (sanitize(item["stage"]), sanitize(item["address"]), item["port"] or "-", sanitize(item["script"]), sanitize(item["output"])))
