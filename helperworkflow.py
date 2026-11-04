import fnmatch
import i18n
import ipaddress
import nmap
import os
import re
import shlex
import yaml

import dbmodule

from dbmodule import BASE_DIR
from helper import isValidTarget, parseArgs, sanitize

WORKFLOWS_DIR = os.path.join(BASE_DIR, "workflows")
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

  def __execute(self, name, net, stages, runId=None, finished=()):
    try:
      nm = nmap.PortScanner()
    except nmap.PortScannerError:
      print(i18n.t("help.help_run_nmap_missing"))
      return
    if runId is None:
      runId = dbmodule.createRun(name, net, stages)
    else:
      dbmodule.setRunStatus(runId, "running")
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
      if not targets:
        dbmodule.setStageStatus(runId, position, "skipped")
        print(label + ": " + i18n.t("help.workflow_no_targets"))
        continue
      if stage["confirm"] and not askConfirmation(label + ": " + i18n.t("help.workflow_confirm_stage") + " " + sanitize(", ".join(target for target, _ in targets))):
        dbmodule.setStageStatus(runId, position, "declined")
        print(label + ": " + i18n.t("help.workflow_declined"))
        continue
      print(label + ": " + i18n.t("help.running_scan"))
      dbmodule.setStageStatus(runId, position, "running")
      try:
        for target, ports in targets:
          arguments = ("-6 " if ":" in target else "") + stage["arguments"]
          nm.scan(hosts=target, ports=ports, arguments=arguments)
          dbmodule.saveStageResults(runId, stage["name"], *collectResults(nm, scope))
      except (nmap.PortScannerError, OSError, dbmodule.lite.Error) as e:
        dbmodule.setStageStatus(runId, position, "failed")
        dbmodule.setRunStatus(runId, "failed")
        print(label + ": " + i18n.t("help.help_run_scan_error") + ": " + sanitize(e))
        print(i18n.t("help.workflow_resume_hint") + ": workflow resume id:" + str(runId))
        return
      except KeyboardInterrupt:
        dbmodule.setStageStatus(runId, position, "interrupted")
        dbmodule.setRunStatus(runId, "interrupted")
        print(label + ": " + i18n.t("help.help_run_interrupted"))
        print(i18n.t("help.workflow_resume_hint") + ": workflow resume id:" + str(runId))
        return
      dbmodule.setStageStatus(runId, position, "completed")
    dbmodule.setRunStatus(runId, "completed")
    self.__printRun(dbmodule.getRun(runId))

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
    if [(stage["name"], stage["arguments"]) for stage in stages] != [(stage["name"], stage["arguments"]) for stage in details["stages"]]:
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
    if not askConfirmation(i18n.t("help.workflow_authorized")):
      print(i18n.t("help.workflow_cancelled"))
      return
    self.__execute(name, net, stages, runId, finished)

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
