#!/bin/bash

dbpath=$(find /usr -type f -name "script.db" 2>/dev/null | awk 'gsub("script.db","")')
nmappath=$(find /usr -type f -name "nmap" 2>/dev/null)
luapath=$(find /usr -type f -name "lua" 2>/dev/null)
luarockspath=$(find /usr -type f -name "luarocks*" 2>/dev/null)

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

if [[ $nmappath ]]; then
  echo "Nmap Found $nmappath"
else
  echo "Installing Nmap"
fi

if [[ $luapath ]]; then
  echo "lua Found $nmappath"
else
  echo "Installing Lua"
fi

if [[ $luarockspath ]]; then
  echo "luarocks Found $luarockspath"
else
  echo "Installing Lua Rocks"
fi
