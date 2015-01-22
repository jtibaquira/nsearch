#!/usr/bin/env lua

local config = require "config"
local filePath = config.filePath
local categoryList = config.categories
local dbmodule = require "dbmodule"
local helper = require "helper"

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
  print " USAGE: lua nsearch.lua or ./nsearch.lua"
end


-- validation of args
if countArgs() < 1 then
  os.execute( "clear" )
  print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
  helper.searchConsole()
else
  helpMenu()
end
