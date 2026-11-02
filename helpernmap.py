import i18n
import nmap
import os
import yaml
import re

class HelperNmap:

  def __init__(self, args):
    self.args = args
    self.net = ""
    self.template = ""
    self.arguments = ""

  def process(self):
    if self.__validateParams():
      print(i18n.t("help.running_scan"))
      nm = nmap.PortScanner()
      nm.scan(hosts=str(self.net), arguments=str(self.arguments))
      for host in nm.all_hosts():
        print('----------------------------------------------------')
        print('Host : %s (%s)' % (host, nm[host].hostname()))
        print('State : %s' % nm[host].state())
        for proto in nm[host].all_protocols():
          print('----------')
          print('Protocol : %s' % proto)
          for port in sorted(nm[host][proto].keys()):
            if nm[host][proto][port]['state'] == 'open':
              print('port : %s\tstate : %s %s %s ' % (port, nm[host][proto][port]['state'], nm[host][proto][port].get("product", ""), nm[host][proto][port].get("version", "")))
              if 'script' in nm[host][proto][port].keys():
                for k,v in nm[host][proto][port]['script'].items():
                  print(k + " => " + v)

  def __validateParams(self):
    argsdic = {}
    if self.args.find('net:') != -1 or self.args.find('template:') != -1:
      if len(self.args.split(":")) == 3:
        argsdic.update({
          self.args.split(":")[0]:self.args.split(":")[1].split(" ")[0],
          self.args.split(":")[1].split(" ")[1]:self.args.split(":")[2].split(" ")[0]
          })
      elif len(self.args.split(":")) == 2:
        argsdic.update({
          self.args.split(":")[0]:self.args.split(":")[1].split(" ")[0]
        })
    else:
      print(i18n.t("help.help_run_error"))
    return self.__setParams(**argsdic)

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
    path = os.path.join(os.getcwd(), "templates", template + ".yaml")
    try:
      with open(path, 'r', encoding="utf-8") as stream:
        self.arguments = yaml.safe_load(stream)[template]["arguments"]
    except (OSError, yaml.YAMLError, KeyError, TypeError):
      print(i18n.t("help.help_run_bad_template"))
      return False
    self.net = net
    return True
