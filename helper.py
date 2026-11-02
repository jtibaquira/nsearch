import dbmodule
import i18n

class Helper:

  def __init__(self, args="", command=""):
    self.args = args
    self.command = command

  #process the commands
  def process(self):
    if self.command == "search":
      if not self.args:
        dbmodule.lastresults = dbmodule.searchAll()
        self.printlastResult()
      elif not self.__searchparams():
        print(i18n.t("help.help_search_error"))
      else:
        dbmodule.lastresults = dbmodule.searchByCriterial(**self.__searchparams())
        self.printlastResult()
    elif self.command == "addfav" and self.args:
      dbmodule.createFavorite(**self.__addfavparams())
    elif self.command == "modfav" and self.args:
      dbmodule.updateFavorite(**self.__modfavparams())
    elif self.command == "delfav" and self.args:
      dbmodule.deleteFavorite(**self.__delfavparams())
    elif self.command == "showfav":
      if not self.args:
        dbmodule.lastresults = dbmodule.getFavorites()
        self.printlastResult(True)
      else:
        dbmodule.lastresults = dbmodule.getFavorites(**self.__showfavparams())
        self.printlastResult(True)
    else:
      print(i18n.t("help.help_command_error"))

  # Display the last results
  def printlastResult(self, fav=False):
    if fav == True:
      print("\033[1;32m*** {0:40} {1:40}\033[0m".format(*["Name","Ranking"]))
      for key,value in dbmodule.lastresults.items():
        print("\033[1;32m[+] {0:40} {1:35}\033[0m".format(*[value["name"],value["ranking"]]))
    else:
      print("\033[1;32m*** {0:40} {1:40}\033[0m".format(*["Name","Author"]))
      for key,value in dbmodule.lastresults.items():
        print("\033[1;32m[+] {0:40} {1:35}\033[0m".format(*[value["name"],value["author"] or ""]))

  # Display the documentation per script
  def displayDoc(self):
    try:
      with open(dbmodule.scriptsPath + self.args, 'r', encoding="utf-8", errors="replace") as scriptFile:
        self.__readLines(scriptFile)
    except Exception as e:
      try:
        with open(dbmodule.scriptsPath + self.args + ".nse", 'r', encoding="utf-8", errors="replace") as scriptFile:
          self.__readLines(scriptFile)
      except Exception as e:
        print(i18n.t("setup.del_fav_error"))

  # used for the autocomplete
  def resultitems(self):
    items = []
    for k,v in dbmodule.lastresults.items():
      items.append(v["name"])
    return items

  # private function to set params for search command
  def __searchparams(self):
    if self.args.find('name:') != -1 or self.args.find('category:') != -1 or self.args.find('author:') != -1:
      return self.__setParams()
    else:
      return False

  #private function to set params for addfav command
  def __addfavparams(self):
    if self.args.find('name:') != -1 or self.args.find('ranking:') != -1:
      return self.__setParams()

  #private function to set params for delfav command
  def __delfavparams(self):
    if self.args.find('name:') != -1:
      return self.__setParams()

  #private function to set params for modfav command
  def __modfavparams(self):
    if self.args.find('name:') != -1 or self.args.find('newname:') != -1 or self.args.find('newranking:') != -1:
      return self.__setParams()

  #private function to set params for showfav command
  def __showfavparams(self):
    if self.args.find('name:') != -1 or self.args.find('ranking:') != -1:
      return self.__setParams()

  # Set Params validations
  def __setParams(self):
    argsdic = {}
    if len(self.args.split(":")) >= 4:
      argsdic.update({
        self.args.split(":")[0]:self.args.split(":")[1].split(" ")[0],
        self.args.split(":")[1].split(" ")[1]:self.args.split(":")[2].split(" ")[0],
        self.args.split(":")[2].split(" ")[1]:self.args.split(":")[3].split(" ")[0]})
    elif len(self.args.split(":")) == 3:
      argsdic.update({
        self.args.split(":")[0]:self.args.split(":")[1].split(" ")[0],
        self.args.split(":")[1].split(" ")[1]:self.args.split(":")[2].split(" ")[0]})
    elif len(self.args.split(":")) == 2:
      argsdic.update({self.args.split(":")[0]:self.args.split(":")[1].split(" ")[0]})
    else:
      print(i18n.t("setup.bad_params"))
    return argsdic

  #Private function to read lines
  def __readLines(self, scriptFile):
    lines = scriptFile.read().splitlines()
    for line in lines:
      if line.startswith("--@output") or line.startswith("-- @output"):
        break
      if not line.lstrip().startswith("local "):
        print('\033[1;96m' + line + '\033[0m')
