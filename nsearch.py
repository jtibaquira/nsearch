#!/usr/bin/env python

import dbmodule
from dbmodule import *
import console
from console import *
import re
import hashlib
import shutil

banner ='\033[0;36m'+'''
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.3     |   @jjtibaquira
  ================================================
'''+'\033[0m'

#create file backups
def createBackUp():
  print i18n.t("setup.create_backup")
  shutil.copy2(dbmodule.filePath, dbmodule.fileBackup)
  if os.path.isfile(dbmodule.fileBackup):
    print i18n.t("setup.create_backup_ok")
  else:
    print i18n.t("setup.create_backup_error")

# init install to the project
def install():
  print banner
  dbmodule.initSetup()
  scriptFile = open(dbmodule.filePath,'r')
  for line in scriptFile:
    line = line.replace('Entry { filename = "',"").replace('", categories = { "',',"').replace('", } }','"').replace('", "','","')
    for i, j in enumerate(dbmodule.categories):
      line = line.replace('"'+j+'"',str(i+1))
    newarray = line.split(",")
    for key,value in enumerate(newarray):
      if value == newarray[0]:
        author = ""
        currentScript = open(dbmodule.scriptsPath+value,'r')
        for line in currentScript:
          if line.startswith("author"):
            author = line.replace('author = "',"").replace('"',',"').replace('[[',"").replace(',"',"").replace("author =","Brandon Enright <bmenrigh@ucsd.edu>, Duane Wessels <wessels@dns-oarc.net>")
        lastrowid = dbmodule.insertScript(value,author)
        currentScript.close()
      else:
        dbmodule.insertScriptCategory(lastrowid,value)
  scriptFile.close()
  createBackUp()

def update():
  print banner
  dbmodule.updateApp()
  #hashlib.md5(open(full_path, 'rb').read()).hexdigest()

# main action
if __name__ == '__main__':

  currentLocale = re.sub('[_].*','',os.environ['LANG'])
  i18n.load_path.append('i18n')
  i18n.set('locale',currentLocale) if True else i18n.set('fallback','en')

  if not os.path.isfile(dbmodule.dbname):
    install()
  else:
    update()

  os.system("clear")
  console = console.Console()
  console.cmdloop()