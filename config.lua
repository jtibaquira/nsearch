-- Module for path configuration

local config = {}

config.filePath = '/usr/local/share/nmap/scripts/script.db'
config.fileBackup = 'scriptbkp.db'
config.scriptdb = 'nmap_scripts.sqlite3'
config.categories = {
                      "auth","broadcast","brute","default","discovery","dos","exploit",
                      "external","fuzzer","intrusive","malware","safe","version","vuln"
                      }
return config
