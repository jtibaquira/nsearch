import dbmodule
import i18n

class Helper:

  def __init__(self,args="",):
    self.args = args

  #process the commnads
  def process(self):
    if not self.args:
      dbmodule.lastresults = dbmodule.searchAll()
      for row in dbmodule.lastresults.items():
        print('\033[1;32m'+str(row[0])+"."+row[1]+'\033[0m')
    else:
      if self.args.find('name:') != -1 and self.args.find('category:') != -1:
        if self.args.startswith('name:'):
          script = self.__processCriterial()
          category = self.__processCriterial(False)
        elif self.args.startswith('category:'):
          script = self.__processCriterial()
          category = self.__processCriterial(False)
        dbmodule.lastresults = dbmodule.searchScriptCategory(script,category)
        self.printlastResult()
      elif self.args.startswith('name:'):
        criterial = self.__processCriterial()
        dbmodule.lastresults = dbmodule.searchScript(criterial)
        self.printlastResult()
      elif self.args.startswith("category:"):
        criterial = self.__processCriterial()
        dbmodule.lastresults = dbmodule.searchCategory(criterial)
        self.printlastResult()
      else:
        print "Use help search for display menu"

  def printlastResult(self):
    for k,v in dbmodule.lastresults.items():
      print('\033[1;32m'+str(k)+"."+v+'\033[0m')

  # Display the documentation per script
  def displayDoc(self):
    scriptFile = open(dbmodule.scriptsPath+self.args,'r')
    lines = scriptFile.read().splitlines()
    for line in lines:
      if line.startswith("license"):
        break
      print('\033[1;96m'+line+'\033[0m')
    scriptFile.close()

  # used for the autocomplete
  def resultitems(self):
    i = 0
    items = []
    for k,v in dbmodule.lastresults.items():
      items.insert(i,v)
      i = i + 1
    return items

  def __processCriterial(self,single=True):
    if single:
      return self.args.split(":")[1].split(" ")[0]
    else:
      return self.args.split(":")[2].split(" ")[0]
