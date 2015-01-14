#!/bin/bash

dbpath=$(find /usr -type f -name "script.db" 2>/dev/null | awk 'gsub("script.db","")')

if [[ $dbpath ]]; then
  echo $dbpath
  echo -e "local settings = {} \n" > settings.lua
  echo -e "settings.scriptsPath='$dbpath'" >> settings.lua
  echo -e "settings.filePath = settings.scriptsPath..'script.db'" >> settings.lua
  echo -e "settings.fileBackup = 'scriptbkp.db'" >> settings.lua
  echo -e "settings.scriptdb = 'nmap_scripts.sqlite3'" >> settings.lua
  echo -e 'settings.categories = {"auth","broadcast","brute","default","discovery","dos","exploit","external","fuzzer","intrusive","malware","safe","version","vuln"}\n' >> settings.lua
  echo -e "return settings" >> settings.lua
fi