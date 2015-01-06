-- db module
local dbmodule = {}

local config = require "config"
local sqlite3 = require "lsqlite3"

function connectDB(scriptdb,method)
  -- local path = system.pathForFile(scriptdb, system.ResourceDirectory)
  if method then
    db = sqlite3.open( scriptdb, method)
  else
    db = sqlite3.open(scriptdb)
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

  local cat = db:prepare [[
  create table categories(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
     name TEXT NOT NULL);
  ]]
  cat:step()
  cat:finalize()

  local config.categories = categoriesList

  for i,v in ipairs(categoryList) do
    print(i,v)
  end

  -- db:exec'INSERT INTO test VALUES(1,2,4)'

  local utable = db:prepare [[
  create table script_category(
    id_category INTEGER NOT NULL,
    id_script INETGER NOT NULL);
  ]]
  utable:step()
  utable:finalize()

  db:close()
end

-- function dbmodule.InsertScript( ... )
  -- body
-- end

-- function dbmodule.UpdateScript( ... )
  -- body
-- end

return dbmodule
