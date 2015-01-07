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

  local  categoryList = config.categories

  for k,v in ipairs(categoryList) do
    print(v)
    sql=[[insert into categories (name) Values (]].."'".. v .. "'"..[[);]]
    print(sql)
    db:exec(sql)
    db:error_message(sql)
  end

  local utable = db:prepare [[
  create table script_category(
    id_category INTEGER NOT NULL,
    id_script INETGER NOT NULL);
  ]]
  utable:step()
  utable:finalize()

  db:close()
end

function dbmodule.InsertScript(value,table)
  sql=[[insert into ]]..table..[[ (name) Values (]].."'".. value .. "'"..[[);]]
  --db:exec(sql)
  --db:error_message(sql)
  print(sql)
end

-- function dbmodule.UpdateScript( ... )
  -- body
-- end

return dbmodule
