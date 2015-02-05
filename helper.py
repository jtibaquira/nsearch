import dbmodule


class Helper:

  def __init__(self,args=""):
    self.args = args

  def process(self):
    if not self.args:
      for row in dbmodule.searchAll():
        print('\033[1;32m'+str(row[0])+"."+row[1]+'\033[0m')
    else:
      criterial = self.args.split(":")[1].split(" ")[0]
      if self.args.startswith('name:'):
        scriptlist = dbmodule.searchScript(criterial)
        for k,v in scriptlist.items():
          print('\033[1;32m'+str(k)+"."+v+'\033[0m')
      elif self.args.startswith("category:"):
        scriptlist = dbmodule.searchCategory(criterial)
        for k,v in scriptlist.items():
          print('\033[1;32m'+str(k)+"."+v+'\033[0m')
      else:
        print "Search all Scripts"