-- Module for path configuration

local config = {}

config.filePath = '/usr/share/nmap/scripts/script.db'
config.fileBackup = 'scriptbkp.db'
config.scriptdb = 'script.sqlite3'
config.categories = {
                      "auth","broadcast","brute","default","discovery","dos","exploit",
                      "external","fuzzer","intrusive","malware","safe","version","vuln"
                      }
return config
