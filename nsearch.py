#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import dbmodule
import os
stream = open("config.yaml", 'r')
item = yaml.load(stream)



if not os.path.isfile(item["config"]["scriptdb"]):
  dbmodule.initSetup(item["config"]["scriptdb"], item["config"]["categories"])
  scriptFile = open(item["config"]["filePath"],'r')
  for line in scriptFile:
    line = line.replace('Entry { filename = "',"").replace('", categories = { "',',"').replace('", } }','"').replace('", "','","')
    for i, j in enumerate(item["config"]["categories"]):
      line = line.replace('"'+j+'"',str(i+1))
    print(lines)
else:
  print("Exist: "+ item["config"]["scriptdb"])
#print item["config"]["scriptsPath"]
#print item["config"]["filePath"]
#print item["config"]["fileBackup"]
#print item["config"]["scriptdb"]
#print item["config"]["categories"]