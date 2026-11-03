import dbmodule
import i18n
import os
import re
import shlex
import sys

from dbmodule import sanitize

def clearScreen():
  if sys.stdout.isatty():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def isValidTarget(net):
  return re.fullmatch(r"[A-Za-z0-9:][A-Za-z0-9.:/,*-]*", net) is not None

def parseArgs(args, allowed):
  """Parse 'key:value' tokens. Returns a dict, or None if the input is invalid."""
  try:
    tokens = shlex.split(args)
  except ValueError:
    return None
  params = {}
  for token in tokens:
    key, sep, value = token.partition(":")
    if not sep or not value or key not in allowed or key in params:
      return None
    params[key] = value
  return params

class Helper:

  def __init__(self, args="", command=""):
    self.args = args
    self.command = command

  # Process the commands
  def process(self):
    if self.command == "search":
      params = parseArgs(self.args, ("name", "category", "author"))
      if params is None:
        print(i18n.t("help.help_search_error"))
        return
      dbmodule.lastresults = (dbmodule.searchByCriterial(**params) if params else dbmodule.searchAll()) or {}
      dbmodule.lastresultsFav = False
      self.printlastResult()
    elif self.command == "addfav":
      params = parseArgs(self.args, ("name", "ranking"))
      if params is None or "name" not in params:
        print(i18n.t("setup.bad_params"))
        return
      dbmodule.createFavorite(**params)
    elif self.command == "modfav":
      params = parseArgs(self.args, ("name", "newname", "newranking"))
      if params is None or "name" not in params or len(params) < 2:
        print(i18n.t("setup.bad_params"))
        return
      dbmodule.updateFavorite(**params)
    elif self.command == "delfav":
      params = parseArgs(self.args, ("name",))
      if not params:
        print(i18n.t("setup.bad_params"))
        return
      dbmodule.deleteFavorite(**params)
    elif self.command == "showfav":
      params = parseArgs(self.args, ("name", "ranking"))
      if params is None:
        print(i18n.t("setup.bad_params"))
        return
      dbmodule.lastresults = dbmodule.getFavorites(**params)
      dbmodule.lastresultsFav = True
      self.printlastResult()
    else:
      print(i18n.t("help.help_command_error"))

  # Display the last results
  def printlastResult(self):
    column = "ranking" if dbmodule.lastresultsFav else "author"
    print("\033[1;32m*** {0:40} {1:40}\033[0m".format("Name", column.capitalize()))
    for value in dbmodule.lastresults.values():
      print("\033[1;32m[+] {0:40} {1:35}\033[0m".format(sanitize(value["name"]), sanitize(value[column] or "")))

  # Display the documentation per script
  def displayDoc(self):
    if not re.fullmatch(r"[\w+-][\w.+-]*", self.args):
      print(i18n.t("help.help_doc_not_found"))
      return
    for name in (self.args, self.args + ".nse"):
      path = os.path.join(dbmodule.scriptsPath, name)
      if os.path.isfile(path):
        with open(path, 'r', encoding="utf-8", errors="replace") as scriptFile:
          self.__readLines(scriptFile)
        return
    print(i18n.t("help.help_doc_not_found"))

  # Used for autocompletion
  def resultitems(self):
    return [value["name"] for value in dbmodule.lastresults.values()]

  # Private function to read the script lines
  def __readLines(self, scriptFile):
    lines = scriptFile.read().splitlines()
    for line in lines:
      if line.startswith("--@output") or line.startswith("-- @output"):
        break
      if not line.lstrip().startswith("local "):
        print('\033[1;96m' + sanitize(line) + '\033[0m')
