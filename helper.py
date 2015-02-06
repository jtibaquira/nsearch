import dbmodule


class Helper:

  def __init__(self,args="",):
    self.args = args

  def process(self):
    if not self.args:
      for row in dbmodule.searchAll():
        print('\033[1;32m'+str(row[0])+"."+row[1]+'\033[0m')
    else:
      if self.args.startswith('name:'):
        criterial = self.args.split(":")[1].split(" ")[0]
        dbmodule.lastresults = dbmodule.searchScript(criterial)
        for k,v in dbmodule.lastresults.items():
          print('\033[1;32m'+str(k)+"."+v+'\033[0m')
      elif self.args.startswith("category:"):
        criterial = self.args.split(":")[1].split(" ")[0]
        dbmodule.lastresults = dbmodule.searchCategory(criterial)
        for k,v in dbmodule.lastresults.items():
          print('\033[1;32m'+str(k)+"."+v+'\033[0m')
      else:
        print "Use help search for display menu"

  def last(self):
    for k,v in dbmodule.lastresults.items():
      print('\033[1;32m'+str(k)+"."+v+'\033[0m')

  def displayDoc(self):
    pass