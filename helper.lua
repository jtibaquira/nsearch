-- Helper Module
--
local setup = require "setup"

local helper = {}

helper.mainMenu = { h = "Help", s = "Initial Setup", n = "Search by Name of Script", c = "Search by Category", b = "Create script.db backup", q = "Exit"}
helper.searchMenu ={ s = "Search by Name", b = "Main Menu", q = "Exit"}

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
  for key,value in pairs(menulist) do
    print("("..key..") "..value)
  end
  return menulist
end

function searchMenu()
  io.write('\n What do you want to do? : ')
  local action = io.read()
  if action == "q" then
    os.exit()
  elseif action == "b" then
   os.execute( "clear" )
    helper.menu(helper.mainMenu)
    helper.Main()
  elseif action == "s" then
    print("Ready for Search")
  else
    os.execute()
  end
end

function helper.Main()
 io.write('\n What do you want to do? : ')
 local action = io.read()
 if action == "q" then
  os.exit()
 elseif action == "s" then
   os.execute( "clear" )
  setup.install(helper.banner())
 elseif action == "n" then
   os.execute( "clear" )
  helper.menu(helper.searchMenu)
  searchMenu()
elseif action == "b" then
  setup.createBackup(helper.banner())
  os.execute( "clear" )
  helper.menu(mainMenu)
  helper.Main()
 else
  os.exit()
 end
end


return helper
