-- Helper Module
--
local setup = require "setup"
local dbmodule = require "dbmodule"
local config = require "config"
scriptdb = config.scriptdb
local helper = {}

function helper.banner()

  banner=[[
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

  return banner
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
    os.execute("clear")
    print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
    helper.searchConsole()
  else
    os.execute("clear")
    print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
    helper.searchConsole()
  end
end

function resultList(nse)
  if #nse > 0 then
    print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
    print("\nTotal Scripts Found "..#nse.."\n")
    for k,v in ipairs(nse) do
      print('\27[92m'..k.." "..v..'\27[0m')
    end
    getScriptDesc(nse)
  else
    print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
    print("\nNot Results Found\n")
    io.write("Do you want search again? [y/n]: ")
    local action = io.read()
    if action == 'y' then
      os.execute("clear")
      print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
      helper.searchConsole()
    else
      os.execute("clear")
      print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
      helper.searchConsole()
    end
   end
end

function resultListaCat(scripts,catName)
  if #scripts > 0 then
    print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
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


function helper.searchConsole()
  if not setup.file_exists(config.scriptdb) then setup.install() end
  io.write('nsearch> ')
  local command = io.read()
  if command == "help" then
    os.execute("clear")
    print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
    print("\tname     : Search by script's name")
    print("\tcategory : Search by category")
    print("\texit     : Close the console")
    print("\tclear    : Clean the console")
    print("\n Usage:")
    print("\n   name:http")
    print("\n   category:exploit \n")
    helper.searchConsole()
  elseif (string.find(command,"name:") and string.find(command,"category:")) then
    print(command)
    helper.searchConsole()
  elseif string.find(command,"name:") then
    string = command:gsub("name:","")
    os.execute("clear")
    resultList(dbmodule.findScript(string))
  elseif string.find(command,"exit") then
    os.exit()
  elseif string.find(command,"clear") then
    os.execute("clear")
    print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
    helper.searchConsole()
  elseif string.find(command,"category:") then
    string = command:gsub("category:","")
    os.execute("clear")
    resultListaCat(dbmodule.SearchByCat(string),string)
  else
   helper.searchConsole()
  end
end

return helper
