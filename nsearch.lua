#!/usr/bin/env lua

local config = require "config"
local filePath = config.filePath
local categoryList = config.categories
local dbmodule = require "dbmodule"
local helper = require "helper"


-- functions to handler the args values
function printArgs()
  for k,v in pairs(arg) do
    print(k,v)
  end
end

-- function to set the total of valid args into the table
function countArgs()
  count = 0
  for _ in pairs(arg) do count = count + 1 end
  return count - 2
end

-- display a Help Menu
function helpMenu()
  local banner = helper.banner()
  print('\27[1m \27[36m'..banner..'\27[21m \27[0m')
  print "NSEarch (0.1)"
  print " USAGE: nsearch [Options] string"
  print " PARAMETERS:"
  print "   -s  create the initial scriptdb for future queries"
  print "   -h  Display this help menu"
  print "   -n  The string to search"
  print "   -b  Create a script.db backup for future diff default name scriptbkp.db the files name are defined in config.lua"
  print " EXAMPLES:"
  print "   nsearch -n http"
  print "   nsearch -c "
  print "   nsearch -s "
end

-- set the each of args
function defineArgs()
  local string
  for i=1,countArgs()  do
    if arg[i] == "-h" then
      helpMenu()
      os.exit()
    elseif arg[i] == "-n" and arg[i+1] ~= nil then
      print("Searching Script...")
      dbmodule.findScript(arg[i+1],helper.banner())
      os.exit()
    elseif arg[i] == "-b" then
      createBackup(lines)
      os.exit()
    elseif arg[i] == "-s" then
      print("NSEarch Initital setup starting...")
      --setup.install(lines)
    elseif arg[i] == "-c" and arg[i+1] ~= nil then
      dbmodule.SearchByCat(arg[i+1])
      os.exit()
    else
      print(arg[i] .." Is not a valid argument, see the help below")
      helpMenu()
      os.exit()
    end
  end
end

-- validation of args
if countArgs() < 1 then
  -- printAll(lines)
  os.execute( "clear" )
--  print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
  helper.searchConsole()
else
  defineArgs()
end
