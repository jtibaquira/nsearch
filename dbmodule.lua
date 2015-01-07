-- db module
local dbmodule = {}

local config = require "config"
local sqlite3 = require "lsqlite3"
scriptdb = config.scriptdb
function connectDB(method)
  -- local path = system.pathForFile(scriptdb, system.ResourceDirectory)
  if method then
    db = sqlite3.open( scriptdb, method)
  else
    db = sqlite3.open(scriptdb)
  end
  return db
end

function dbmodule.InitSetup(method)
  local db = connectDB(scriptdb,method)
  local sm = db:prepare [[
  create table scripts(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
      name TEXT NOT NULL,
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
    sql=[[insert into categories (name) Values (]].."'".. v .. "'"..[[);]]
    db:exec(sql)
    --print(db:last_insert_rowid(sql))
    --print(db:error_message(sql))
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
  local db = connectDB(scriptdb,"wc")
  for i,v in ipairs(value) do
    sql=[[insert into ]]..table..[[ (name) Values (]].."'".. v .. "'"..[[);]]
    db:exec(sql)
  end
  db:close()
  return last_rowid
end


function dbmodule.InsertCategory(id_script,id_category)
  local db = connectDB(scriptdb,"wc")
   sql=[[insert into script_category (id_category,id_script) Values (]].. id_category ..",".. id_script ..[[);]]
   db:exec(sql)
   db:close()
end

-- function dbmodule.UpdateScript( ... )
  -- body
-- end

return dbmodule
