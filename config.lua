-- Module for path configuration

local config = {}

config.scriptsPath = '/usr/local/share/nmap/scripts/'
config.filePath = config.scriptsPath..'script.db'
config.fileBackup = 'scriptbkp.db'
config.scriptdb = 'nmap_scripts.sqlite3'
config.categories = {
                      "auth","broadcast","brute","default","discovery","dos","exploit",
                      "external","fuzzer","intrusive","malware","safe","version","vuln"
                      }
return config
