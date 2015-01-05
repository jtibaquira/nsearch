#!/usr/bin/env lua

local config = require "config"
local filePath = config.filePath

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
  print "Nse-Script-Search (0.1)"
  print " USAGE: search-script [Options] string"
  print " PARAMETERS:"
  print "   -h  Display this help menu"
  print "   -n  The string to search"
  print "   -c  Create a script.db backup for future diff <default name scriptbkp.db>"
  print " EXAMPLES:"
  print "   search-script -n http"
  print "   search-script -c /path/script.db/ /path/for/backup"
end

-- see if the file exists
function file_exists(file)
  local f = io.open(file, "rb")
  if f then f:close() end
  return f ~= nil
end

-- get all lines from a file, returns an empty
-- list/table if the file does not exist
function lines_from(file)
  if not file_exists(file) then print "El archivo no existe" os.exit() end
  lines = {}
  for line in io.lines(file) do
    lines[#lines + 1] = line
  end
  return lines
end

-- tests the functions above
local file = filePath
local lines = lines_from(file)
-- print all line numbers and their contents

function printAll(lines)
  for k,v in pairs(lines) do
    print(v)
  end
end

function printResults(lines,script)
  local count = 0
  for k,v in pairs(lines) do
    local i = string.find(v, script)
    v = v:gsub('%Entry { filename = "',"")
    v = v:gsub('", categories = { "',', ["')
    v = v:gsub('", } }','"]')
    if i ~= nil then print(v) count = count + 1 end
  end
  if count == 0 then print("Script not Found") end
end

-- set the each of args
function defineArgs()
  local string
  for i=1,countArgs()  do
    if arg[i] == "-h" then
      helpMenu()
      os.exit()
    elseif arg[i] == "-n" then
      string = arg[i+1] printResults(lines,string)
      os.exit()
    elseif arg[i] == "-c" then
      print("For Create a new backup")
    else
      print(arg[i] .." Is not a valid argument, see the help below")
      helpMenu()
      os.exit()
    end
  end
end

-- validation of args
if countArgs() < 1 then
  printAll(lines)
else
  defineArgs()
end