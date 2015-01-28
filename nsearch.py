#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import dbmodule
import os
import sys

stream = open("config.yaml", 'r')
item = yaml.load(stream)

dbname = item["config"]["scriptdb"]
categories = item["config"]["categories"]
filePath = item["config"]["filePath"]
fileBackup = item["config"]["fileBackup"]
scriptsPath = item["config"]["scriptsPath"]

banner ='''
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.2     |   @jjtibaquira
  ================================================
'''

def main():
  os.system("clear")
  print('\033[0;36m'+banner+'\033[0m')
  mainConsole()

def createBackUp():
  print("Creating Script.db Backup ... ")
  scriptFile = open(filePath,'r')
  for line in scriptFile:
    script = open(fileBackup,'a')
    script.write(line,)
  if os.path.isfile(fileBackup):
    print "The Backup was created successfully"
    script.close()
    scriptFile.close()
  else:
    print "The Backup was not created"


def install():
  dbmodule.initSetup(dbname, categories)
  scriptFile = open(filePath,'r')
  for line in scriptFile:
    line = line.replace('Entry { filename = "',"").replace('", categories = { "',',"').replace('", } }','"').replace('", "','","')
    for i, j in enumerate(categories):
      line = line.replace('"'+j+'"',str(i+1))
    newarray = line.split(",")
    for key,value in enumerate(newarray):
      if value == newarray[0]:
        lastrowid = dbmodule.insertScript(dbname,value)
      else:
        dbmodule.insertScriptCategory(dbname,lastrowid,value)
  scriptFile.close()
  createBackUp()


def mainConsole():
  if not os.path.isfile(dbname):
    install()
  is_valid=0
  while not is_valid :
    try :
      command = raw_input('nsearch> ')
      is_valid = 1 ## set it to 1 to validate input and to terminate the while..not loop
    except ValueError, e :
      print ("'%s' is not a valid command." % e.args[0].split(": ")[1])
      mainConsole()
  if command == "help":
    print("\tname     : Search by script's name")
    print("\tcategory : Search by category")
    print("\texit     : Close the console")
    print("\tclear    : Clean the console")
    print("\n\t Usage:")
    print("\t   name:http")
    print("\t   category:exploit \n")
    mainConsole()
  elif command == "exit":
    sys.exit(0)
  elif command == "clear":
    os.system("clear")
    main()
  else:
    mainConsole()

if __name__ == "__main__":
  main()