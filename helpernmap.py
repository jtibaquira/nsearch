import i18n
import nmap
import os
import re
import yaml

from dbmodule import BASE_DIR
from helper import parseArgs, sanitize

class HelperNmap:

  def __init__(self, args):
    self.args = args
    self.net = ""
    self.template = ""
    self.arguments = ""

  def process(self):
    if self.__validateParams():
      print(i18n.t("help.running_scan"))
      try:
        nm = nmap.PortScanner()
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
        print('Host : %s (%s)' % (sanitize(host), sanitize(nm[host].hostname())))
        print('State : %s' % sanitize(nm[host].state()))
        for proto in nm[host].all_protocols():
          print('----------')
          print('Protocol : %s' % sanitize(proto))
          for port in sorted(nm[host][proto].keys()):
            info = nm[host][proto][port]
            if info['state'] == 'open':
              print('port : %s\tstate : %s %s %s ' % (port, sanitize(info['state']), sanitize(info.get('product', '')), sanitize(info.get('version', ''))))
              for k, v in info.get('script', {}).items():
                print(sanitize(k) + " => " + sanitize(v))

  def __validateParams(self):
    params = parseArgs(self.args, ("net", "template"))
    if params is None:
      print(i18n.t("help.help_run_error"))
      return False
    return self.__setParams(**params)

  #private function to set params
  def __setParams(self, **kwargs):
    if "net" not in kwargs or "template" not in kwargs:
      print(i18n.t("help.help_run_error"))
      return False
    net = kwargs["net"]
    template = kwargs["template"]
    if not re.fullmatch(r"[A-Za-z0-9:][A-Za-z0-9.:/,*-]*", net):
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
