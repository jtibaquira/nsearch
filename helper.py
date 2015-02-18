import dbmodule
import i18n
import re

class Helper:

  def __init__(self,args="",):
    self.args = args

  def process(self):
    if not self.args:
      dbmodule.lastresults = dbmodule.searchAll()
      for row in dbmodule.lastresults.items():
        print('\033[1;32m'+str(row[0])+"."+row[1]+'\033[0m')
    else:
      if self.args.find('name:') != -1 and self.args.find('category:') != -1:
        if self.args.startswith('name:'):
          script = self.args.split(":")[1].split(" ")[0]
          category = self.args.split(":")[2].split(" ")[0]
        elif self.args.startswith('category:'):
          script = self.args.split(":")[1].split(" ")[0]
          category = self.args.split(":")[2].split(" ")[0]
        dbmodule.lastresults = dbmodule.searchScriptCategory(script,category)
        for k,v in dbmodule.lastresults.items():
          print('\033[1;32m'+str(k)+"."+v+'\033[0m')
      elif self.args.startswith('name:'):
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
    scriptFile = open(dbmodule.scriptsPath+self.args,'r')
    lines = scriptFile.read().splitlines()
    for line in lines:
      if line.startswith("license"):
        break
      print('\033[1;96m'+line+'\033[0m')
    scriptFile.close()

  def resultitems(self):
    i = 0
    items = []
    for k,v in dbmodule.lastresults.items():
      items.insert(i,v)
      i = i + 1
    return items
