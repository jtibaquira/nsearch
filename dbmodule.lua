-- db module
local dbmodule = {}

local config = require "config"
local sqlite3 = require "sqlite3"

function connectDB(scriptdb,method)
  local path = system.pathForFile(scriptdb, system.ResourceDirectory)
  if method then
    db = sqlite3.open( path, method)
  else
    db = sqlite3.open( path)
  end
  return db
end

function dbmodule.InitSetup( scriptdb, method)
  local db = connectDB(scriptdb,method)
  local sm = db:prepare [[
  create table scripts(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
      name TEXT NOT NULL,
      categor TEXT NOT NULL,
      author TEXT NULL);
  ]]
  sm:step()
  sm:finalize()
  db:close()
end

function dbmodule.InsertScript( ... )
  -- body
end

function dbmodule.UpdateScript( ... )
  -- body
end

return dbmodule