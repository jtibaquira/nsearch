-- Helper Module
--
local helper = {}
local setup = require "setup"

helper.mainMenu = { h = "Help", s = "Initial Setup", n = "Search by Name of Script", c = "Search by Category", b = "Create script.db backup", q = "Exit"}
helper.searchMenu ={ s = "Search by Name", m = "Main Menu", q = "Exit"}

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

function helper.Main(lines)
 io.write('\n What do you want to do? : ')
 local action = io.read()
 print(action)
 if action == "q" then
  os.exit()
 elseif action == "s" then
  setup.install(lines,helper.banner())
 elseif action == "n" then
  helper.menu(helper.searchMenu)
 else
  os.exit()
 end
end


return helper
