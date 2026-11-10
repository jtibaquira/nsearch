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


class HelperNmap:

  def __init__(self, args):
    self.args = args
    self.net = ""
    self.template = ""
    self.arguments = ""

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
      for host in nm.all_hosts():
        print('----------------------------------------------------')
        print(f"Host : {sanitize(host)} ({sanitize(nm[host].hostname())})")
        print(f"State : {sanitize(nm[host].state())}")
        for proto in nm[host].all_protocols():
          print('----------')
          print(f"Protocol : {sanitize(proto)}")
          for port in sorted(nm[host][proto].keys()):
            info = nm[host][proto][port]
            if info['state'] == 'open':
              print(f"port : {port}\tstate : {sanitize(info['state'])} {sanitize(info.get('product', ''))} {sanitize(info.get('version', ''))} ")
              for k, v in info.get('script', {}).items():
                print(sanitize(k) + " => " + sanitize(v))

  def __validateParams(self):
    params = parseArgs(self.args, ("net", "template"))
    if params is None:
      print(i18n.t("help.help_run_error"))
      return False
    return self.__setParams(**params)

  # Private function to validate and set the params
  def __setParams(self, **kwargs):
    if "net" not in kwargs or "template" not in kwargs:
      print(i18n.t("help.help_run_error"))
      return False
    net = kwargs["net"]
    template = kwargs["template"]
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
