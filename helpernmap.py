import nmap

class HelperNmap:

  def __init__(self,args=""):
    self.args = args

  def process(self):
    print "Running Scan"
    nm = nmap.PortScanner()
    nm.scan(hosts='173.255.243.189', arguments='-sV -p1-5000')
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
            print ('port : %s\tstate : %s, %s %s ' % (port, nm[host][proto][port]['product'], nm[host][proto][port]['version'], nm[host][proto][port]['cpe']))
