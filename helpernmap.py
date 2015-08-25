import i18n
import nmap
import os
import yaml

class HelperNmap:

  def __init__(self,args):
    self.args = args
    self.net = ""
    self.template = ""

  def process(self):
    if self.__validateParams():
      print i18n.t("help.running_scan")
      nm = nmap.PortScanner()
      nm.scan(hosts=str(self.net), arguments=str(self.arguments))
      for host in nm.all_hosts():
        print('----------------------------------------------------')
        print('Host : %s (%s)' % (host, nm[host].hostname()))
        print('State : %s' % nm[host].state())
        for proto in nm[host].all_protocols():
          print('----------')
          print('Protocol : %s' % proto)
          lport = nm[host][proto].keys()
          lport.sort()
          for port in lport:
            if nm[host][proto][port]['state'] == 'open':
              print ('port : %s\tstate : %s %s %s ' % (port, nm[host][proto][port]['state'], nm[host][proto][port]['product'], nm[host][proto][port]['version']))
              if 'script' in nm[host][proto][port].keys():
                for k,v in nm[host][proto][port]['script'].items():
                  print k+" => "+v
              else:
                pass
    else:
      pass

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
        pass
    else:
      print i18n.t("help.help_run_error")
    return self.__setParams(**argsdic)

  #private function to set params
  def __setParams(self,**kwargs):
    if kwargs is not None:
      if kwargs.has_key("net") and kwargs.has_key("template"):
        net = kwargs["net"]
        arguments = kwargs["template"]
        self.net = net
        stream = open(os.getcwd()+"/templates/"+arguments+".yaml","r")
        item = yaml.load(stream)
        values =item[arguments]["arguments"]
        self.arguments = values
        return True
      else:
        return False
    else:
      return False
