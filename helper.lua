-- Helper Module
--
local setup = require "setup"
local dbmodule = require "dbmodule"
local helper = {}

helper.mainMenu = {"Help (h)", "Initial Setup (i)", "Search by Name of Script (s)", "Search by Category (c)", "Create script.db backup (b)", "Exit (q)"}
helper.searchMenu ={ "Search by Name (s)", "Main Menu (b)", "Exit (q)"}

function helper.banner()

  banner=[[
   _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_ \
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ]]

  return banner
end


function helper.menu(menulist)
  print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
  for key,value in ipairs(menulist) do
    print(key.." "..value)
  end
  return menulist
end

function searchConsole()
  --print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
  io.write('\nnsearch> ')
  local command = io.read()
  if command == "help" or command == nil then
    os.execute("clear")
    print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
    print("name : to search by script's name ")
    print("\n Usage name:http")
    searchConsole()
  elseif string.find(command,"name:") then
    string = command:gsub("name:","")
    print(string)
    dbmodule.findScript(string,helper.banner())
  else
    print("bad string")
   searchConsole()
  end
end

function searchMenu()
  io.write('\n What do you want to do? : ')
  local action = io.read()
  if action == "q" or action == "3" then
    os.exit()
  elseif action == "b" or action == "2" then
   os.execute( "clear" )
    helper.menu(helper.mainMenu)
    helper.Main()
  elseif action == "s" or action == "1" then
    os.execute("clear")
    print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
    searchConsole()
  else
    os.execute()
  end
end

function helper.Main()
 io.write('\n What do you want to do? : ')
 local action = io.read()
 if action == "q" or action == "6" then
  os.exit()
 elseif action == "i" or action == "2" then
   os.execute( "clear" )
  setup.install(helper.banner())
 elseif action == "s" or action == "3" then
   os.execute( "clear" )
  helper.menu(helper.searchMenu)
  searchMenu()
elseif action == "b" or action == "4" then
  setup.createBackup(helper.banner())
  os.execute( "clear" )
  helper.menu(mainMenu)
  helper.Main()
 else
  os.exit()
 end
end


return helper
