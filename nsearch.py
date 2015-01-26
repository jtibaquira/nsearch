#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import dbmodule
import os

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

def createBackUp():
  print "createBackUp"


def install():
  print(banner)
  if not os.path.isfile(dbname):
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
  else:
    print("Exist: "+ dbname)

install()