#!/usr/bin/env lua

local config = require "config"
local filePath = config.filePath
local categoryList = config.categories
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
  print "   -s  create the initial scriptdb for future queries"
  print "   -h  Display this help menu"
  print "   -n  The string to search"
  print "   -c  Create a script.db backup for future diff <default name scriptbkp.db> the files name are defined in config.lua"
  print " EXAMPLES:"
  print "   search-script -n http"
  print "   search-script -c "
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
  local t ={}
  for k,v in pairs(lines) do
    local i = string.find(v, script)
    v = v:gsub('%Entry { filename = "',""):gsub('", categories = { "',',"'):gsub('", } }','"'):gsub('", "','","')
    for i,c in ipairs(categoryList) do
      v = v:gsub('"'..c..'"',i)
    end
    for a in string.gmatch(v,"([^,]+)") do
      table.insert(t,a)
    end
    for key,value in ipairs(t) do
      if t[1] == value then
       print(value.." it's a scriptdb")
      else
       print(value.." it's a categorie")
      end
    end
    t = {}
    if i ~= nil then count = count + 1 end
  end
  if count == 0 then print("Script not Found") end
end

-- create a script.db backups
function createBackup(lines)
  outfile = io.open(config.fileBackup, "w")
  for k,v in pairs(lines) do
    outfile:write(v.."\n")
  end
  outfile:close()
  if not file_exists(config.fileBackup) then
    print "the backup can not created"
    os.exit()
  else
    print "backup succesfull"
  end
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
      createBackup(lines)
      os.exit()
    elseif arg[i] == "-s" then
      print("NSEarch Initital setup starting...")
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
