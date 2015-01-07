-- db module
local dbmodule = {}

local config = require "config"
local sqlite3 = require "lsqlite3"
scriptdb = config.scriptdb
function connectDB(method)
  if method then
    db = sqlite3.open( scriptdb, method)
  else
    db = sqlite3.open(scriptdb)
  end
  return db
end

function findAll(table)
  local db = connectDB()
  for row in db:nrows("Select name from "..table.." ") do
    print(">>> "..row.name)
  end
end


function dbmodule.InitSetup(method)
  local db = connectDB(scriptdb,method)
  print("Creating Database :"..scriptdb)
  local sm = db:prepare [[
  create table scripts(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
      name TEXT NOT NULL,
      author TEXT NULL);
  ]]
  sm:step()
  print("Creating Table For Script ....")
  sm:finalize()

  local cat = db:prepare [[
   create table categories(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
     name TEXT NOT NULL);
  ]]
  cat:step()
  print("Creating Table for Categories .... ")
  cat:finalize()

  local sc = db:prepare [[
  create table script_category(
    id_category INTEGER NOT NULL,
    id_script INETGER NOT NULL);
  ]]
  sc:step()
  print("Creating Table for Scripts per Category ....")
  sc:finalize()

  local  categoryList = config.categories
  print("Upload Categories to Categories Table ...")
  for k,v in ipairs(categoryList) do
    sql=[[insert into categories (name) Values (]].."'".. v .. "'"..[[);]]
    db:exec(sql)
  end
  db:close()
end

function dbmodule.InsertScript(value,table)
  local db = connectDB(scriptdb,"wc")
  for i,v in ipairs(value) do
    sql=[[insert into ]]..table..[[ (name) Values (]].."'".. v .. "'"..[[);]]
    db:exec(sql)
    last_rowid = db:last_insert_rowid(sql)
  end
  db:close()
  return last_rowid
end


function dbmodule.InsertCategory(id_script,id_category)
  local db = connectDB(scriptdb,"wc")
  -- print("Upload Scripts per Category to  Table ...")
   sql=[[insert into script_category (id_category,id_script) Values (]].. id_category ..",".. id_script ..[[);]]
   db:exec(sql)
   db:close()
end

function dbmodule.SearchByCat(catName)
  scripts = {}
  local db = connectDB("wc")
  for row in db:nrows("select scripts.name from scripts, categories, script_category where categories.name='"..catName.."' and scripts.id=script_category.id_script and categories.id=script_category.id_category") do
    table.insert(scripts,row.name)
  end
  if #scripts > 0 then
    print("\nTotal Scripts Found "..#scripts.." into "..catName.." Category\n")
    for k,v in ipairs(scripts) do
      print(k.." "..v)
    end
   else
     print("Not Results Found\n")
     print("=== These are the enabled Categories ===\n")
     findAll("categories")
  end
  --sql=[[select scripts.name from scripts, categories, script_category where categories.name="default" and scripts.id=script_category.id_script and categories.id=script_category.id_category;]]
  --db:exec(sql)
  db:close()
  --return scripts
end


return dbmodule
