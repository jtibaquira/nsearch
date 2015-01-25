#!/usr/bin/env lua

local setup = require "setup"
local dbmodule = require "dbmodule"
local config = require "config"
local categoryList = config.categories
local filePath = config.filePath
local scriptdb = config.scriptdb


local banner=[[
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_ \
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.2     |   @jjtibaquira
  ================================================
  ]]


function file_exists(file)
  local f = io.open(file, "rb")
  if f then f:close() end
  return f ~= nil
end

-- get all lines from a file, returns an empty
-- list/table if the file does not exist
function lines_from(file)
  if not file_exists(file) then print "File don't exist" os.exit() end
  lines = {}
  for line in io.lines(file) do
    lines[#lines + 1] = line
  end
  return lines
end

-- tests the functions above
local file = filePath
local lines = lines_from(file)

-- create a script.db backups
function createBackup()
  outfile = io.open(config.fileBackup, "w")
  for k,v in pairs(lines) do
    outfile:write(v.."\n")
  end
  outfile:close()
  if not file_exists(config.fileBackup) then
    print "the backup can not created"
  else
    print "backup succesfull"
  end
end

function install()
  dbmodule.InitSetup("wc")
  local t ={}
  local id_script = 0
  for k,v in ipairs(lines) do
    v = v:gsub('%Entry { filename = "',""):gsub('", categories = { "',',"'):gsub('", } }','"'):gsub('", "','","')
    for i,c in ipairs(categoryList) do
      v = v:gsub('"'..c..'"',i)
    end
    for a in string.gmatch(v,"([^,]+)") do
      table.insert(t,a)
    end
    for key,value in ipairs(t) do
      if t[1] == value then
        local val = {value}
        id_script = dbmodule.InsertScript(val,"scripts")
      else
        dbmodule.InsertCategory(id_script,value)
      end
    end
    t = {}
  end
  createBackup()
end


function returnConsole()
  os.execute("clear")
  print('\27[1m \27[36m'..banner..'\27[21m \27[0m')
  searchConsole()
end

function getScriptDesc( nse )
  io.write('\nDo yo want more info about any script, choose the script using id [1-'..#nse..'] or quit (0)')
  local option  = io.read()
  key = tonumber(option)
  if nse[key] then
    print("\n")
    local file = config.scriptsPath..nse[key]
    local lines = lines_from(file)
    for k,v in pairs(lines) do
      local i = string.find(v, "license")
      if not i then
        print('\27[96m'..v..'\27[0m')
      else
        getScriptDesc(nse)
      end
    end
  elseif option == "0" then
    returnConsole()
  else
    returnConsole()
  end
end

function resultList(nse)
  if #nse > 0 then
    print('\27[1m \27[36m'..banner..'\27[21m \27[0m')
    print("\nTotal Scripts Found "..#nse.."\n")
    for k,v in ipairs(nse) do
      print('\27[92m'..k.." "..v..'\27[0m')
    end
    getScriptDesc(nse)
  else
    print('\27[1m \27[36m'..banner..'\27[21m \27[0m')
    print("\nNot Results Found\n")
    io.write("Do you want search again? [y/n]: ")
    local action = io.read()
    if action == 'y' then
      returnConsole()
    else
      returnConsole()
    end
   end
end

function resultListaCat(scripts,catName)
  if #scripts > 0 then
    print('\27[1m \27[36m'..banner..'\27[21m \27[0m')
    print("\nTotal Scripts Found "..#scripts.." into "..catName.." Category\n")
    for k,v in ipairs(scripts) do
      print('\27[92m'..k.." "..v..'\27[0m')
    end
    getScriptDesc(scripts)
   else
     print("Not Results Found\n")
     print("=== These are the enabled Categories ===\n")
     dbmodule.findAll("categories")
  end
end


function searchConsole()
  if not file_exists(config.scriptdb) then install() end
  io.write('nsearch> ')
  local command = io.read()
  if command == "help" then
    os.execute("clear")
    print('\27[1m \27[36m'..banner..'\27[21m \27[0m')
    print("\tname     : Search by script's name")
    print("\tcategory : Search by category")
    print("\texit     : Close the console")
    print("\tclear    : Clean the console")
    print("\n\t Usage:")
    print("\t   name:http")
    print("\t   category:exploit \n")
    searchConsole()
  elseif (string.find(command,"name:") and string.find(command,"category:")) then
    print(command)
    searchConsole()
  elseif string.find(command,"name:") then
    string = command:gsub("name:","")
    os.execute("clear")
    resultList(dbmodule.findScript(string))
  elseif string.find(command,"exit") then
    os.exit()
  elseif string.find(command,"clear") then
    os.execute("clear")
    returnConsole()
  elseif string.find(command,"category:") then
    string = command:gsub("category:","")
    os.execute("clear")
    resultListaCat(dbmodule.SearchByCat(string),string)
  else
   searchConsole()
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
  print('\27[1m \27[36m'..banner..'\27[21m \27[0m')
  print " USAGE: lua nsearch.lua or ./nsearch.lua"
end

-- validation of args
if countArgs() < 1 then
  returnConsole()
else
  helpMenu()
end