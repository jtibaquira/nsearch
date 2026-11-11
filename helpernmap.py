import ntpath
import os
import re
import shlex
import sys

import i18n
import nmap
import yaml

import dbmodule
from dbmodule import BASE_DIR
from helper import isValidTarget, parseArgs, sanitize
from scriptpolicy import analyzeScriptExpression, askConfirmation

WINDOWS_NMAP = (r"C:\Program Files (x86)\Nmap\nmap.exe", r"C:\Program Files\Nmap\nmap.exe")

# The output name is a single file name saved in reports/ as .txt, so it cannot point anywhere else
def normalizeOutputName(name):
  if not name or name.endswith((" ", ".")):
    return None
  extension = os.path.splitext(name)[1].lower()
  if extension not in ("", ".txt"):
    return None
  stem = name[:-4] if extension == ".txt" else name
  if not stem or stem in (".", "..") or stem.endswith((" ", ".")):
    return None
  if any(ord(character) < 32 or character in '<>:"/\\|?*' for character in stem):
    return None
  reserved = {"CON", "PRN", "AUX", "NUL"}
  reserved.update("COM" + str(number) for number in range(1, 10))
  reserved.update("LPT" + str(number) for number in range(1, 10))
  if stem.split(".", 1)[0].upper() in reserved:
    return None
  return stem + ".txt"

# On Windows, only the nmap.exe next to the configured scripts folder or in the standard install folders is run.
# A bare "nmap" would also be looked up in the current folder and in PATH, where a fake nmap.exe could be waiting
def newScanner():
  if sys.platform == "win32":
    scriptsPath = dbmodule.scriptsPath
    drive, _ = ntpath.splitdrive(scriptsPath)
    configured = ntpath.join(ntpath.dirname(ntpath.normpath(scriptsPath)), "nmap.exe") if scriptsPath else ""
    if drive and ntpath.isabs(scriptsPath) and ntpath.isabs(configured):
      return nmap.PortScanner(nmap_search_path=(configured,) + WINDOWS_NMAP)
    return nmap.PortScanner(nmap_search_path=WINDOWS_NMAP)
  return nmap.PortScanner()

def renderScanResults(nm):
  lines = []
  for host in nm.all_hosts():
    lines.append('----------------------------------------------------')
    lines.append(f"Host : {sanitize(host)} ({sanitize(nm[host].hostname())})")
    lines.append(f"State : {sanitize(nm[host].state())}")
    for proto in nm[host].all_protocols():
      lines.append('----------')
      lines.append(f"Protocol : {sanitize(proto)}")
      for port in sorted(nm[host][proto].keys()):
        info = nm[host][proto][port]
        if info['state'] == 'open':
          lines.append(f"port : {port}\tstate : {sanitize(info['state'])} {sanitize(info.get('product', ''))} {sanitize(info.get('version', ''))} ")
          for k, v in info.get('script', {}).items():
            lines.append(sanitize(k) + " => " + sanitize(v))
  return "".join(line + "\n" for line in lines)


class HelperNmap:

  def __init__(self, args):
    self.args = args
    self.net = ""
    self.template = ""
    self.arguments = ""
    self.output = None

  def process(self):
    if self.__validateParams() and self.__confirmScripts():
      print(i18n.t("help.running_scan"))
      try:
        nm = newScanner()
      except nmap.PortScannerError:
        print(i18n.t("help.help_run_nmap_missing"))
        return
      try:
        nm.scan(hosts=str(self.net), arguments=str(self.arguments))
      except nmap.PortScannerError as e:
        print(i18n.t("help.help_run_scan_error") + ": " + sanitize(e))
        return
      except KeyboardInterrupt:
        print(i18n.t("help.help_run_interrupted"))
        return
      content = renderScanResults(nm)
      print(content, end="")
      if self.output is not None:
        import helperworkflow
        try:
          path = helperworkflow.writeRunOutput(self.output, content)
        except OSError as e:
          print(i18n.t("help.help_run_output_error") + ": " + sanitize(e))
          return
        print(i18n.t("help.help_run_output_saved") + ": " + sanitize(path))

  def __validateParams(self):
    params = parseArgs(self.args, ("net", "template", "output"))
    if params is None:
      try:
        tokens = shlex.split(self.args)
      except ValueError:
        tokens = []
      if "output:" in tokens:
        print(i18n.t("help.help_run_bad_output"))
      else:
        print(i18n.t("help.help_run_error"))
      return False
    if not self.__setParams(**params):
      return False
    if self.output is not None:
      import helperworkflow
      if os.path.lexists(os.path.join(helperworkflow.REPORTS_DIR, self.output)):
        print(i18n.t("help.help_run_output_exists"))
        return False
    return True

  # Private function to validate and set the params
  def __setParams(self, **kwargs):
    if "net" not in kwargs or "template" not in kwargs:
      print(i18n.t("help.help_run_error"))
      return False
    net = kwargs["net"]
    template = kwargs["template"]
    output = kwargs.get("output")
    if output is not None:
      output = normalizeOutputName(output)
      if output is None:
        print(i18n.t("help.help_run_bad_output"))
        return False
    if not isValidTarget(net):
      print(i18n.t("help.help_run_bad_target"))
      return False
    if not re.fullmatch(r"[A-Za-z0-9_-]+", template):
      print(i18n.t("help.help_run_bad_template"))
      return False
    path = os.path.join(BASE_DIR, "templates", template + ".yaml")
    try:
      with open(path, 'r', encoding="utf-8") as stream:
        self.arguments = yaml.safe_load(stream)[template]["arguments"]
    except (OSError, yaml.YAMLError, KeyError, TypeError):
      print(i18n.t("help.help_run_bad_template"))
      return False
    self.net = net
    self.output = output
    return True

  def __scriptExpressions(self):
    try:
      tokens = shlex.split(str(self.arguments))
    except ValueError:
      return re.findall(r"--script(?:=|\s+)([^\s]+)", str(self.arguments)), "--script" in str(self.arguments)
    expressions = []
    unparsed = False
    index = 0
    while index < len(tokens):
      token = tokens[index]
      index += 1
      if token == "--script":
        if index < len(tokens):
          expressions.append(tokens[index])
          index += 1
        else:
          unparsed = True
      elif token.startswith("--script="):
        value = token.partition("=")[2]
        if value:
          expressions.append(value)
        else:
          unparsed = True
    return expressions, unparsed

  def __confirmScripts(self):
    expressions, unparsed = self.__scriptExpressions()
    if not expressions and not unparsed:
      return True
    try:
      scripts = dbmodule.scriptCategories()
    except (dbmodule.lite.Error, OSError):
      scripts = {}
    analyses = [analyzeScriptExpression(expression, scripts, template=True) for expression in expressions]
    if any(item["folder"] for item in analyses):
      print(i18n.t("help.help_run_blocked_folder"))
      return False
    if any(item["blockedSelected"] for item in analyses):
      print(i18n.t("help.help_run_blocked_scripts"))
      return False
    reasons = []
    if any(item["unsafe"] for item in analyses):
      reasons.append(i18n.t("help.help_run_reason_unsafe"))
    if any(item["external"] for item in analyses):
      reasons.append(i18n.t("help.help_run_reason_external"))
    if any(item["hasNot"] for item in analyses):
      reasons.append(i18n.t("help.help_run_reason_not"))
    if unparsed or any(not item["parsed"] for item in analyses):
      reasons.append(i18n.t("help.help_run_reason_unverified"))
    if not reasons:
      return True
    print(i18n.t("help.help_run_plan") + ": " + sanitize(self.net))
    print("  " + sanitize(self.arguments))
    print("  " + i18n.t("help.help_run_reason") + ": " + "; ".join(reasons))
    if not askConfirmation(i18n.t("help.help_run_confirm")):
      print(i18n.t("help.help_run_cancelled"))
      return False
    return True
