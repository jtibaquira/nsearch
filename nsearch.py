#!/usr/bin/env python

import dbmodule
import os
import sys
import console


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

def createBackUp():
  print("Creating Script.db Backup ... ")
  scriptFile = open(dbmodule.filePath,'r')
  for line in scriptFile:
    script = open(dbmodule.fileBackup,'a')
    script.write(line,)
  if os.path.isfile(dbmodule.fileBackup):
    print "The Backup was created successfully"
    script.close()
    scriptFile.close()
  else:
    print "The Backup was not created"


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
        lastrowid = dbmodule.insertScript(value)
      else:
        dbmodule.insertScriptCategory(lastrowid,value)
  scriptFile.close()
  createBackUp()

if __name__ == '__main__':
  if not os.path.isfile(dbmodule.dbname):
    install()
  os.system("clear")
  console = console.Console()
  console.cmdloop()