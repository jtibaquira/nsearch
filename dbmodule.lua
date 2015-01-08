-- db module
local dbmodule = {}

local config = require "config"
local sqlite3 = require "lsqlite3"
scriptdb = config.scriptdb
local helper = require "helper"
-- see if the file exists
function file_exists(file)
  local f = io.open(file, "rb")
  if f then f:close() end
  return f ~= nil
end

-- get all lines from a file, returns an empty
-- list/table if the file does not exist
function lines_from(file)
  if not file_exists(file) then print "El archivo no existe" os.exit() end
  lines = {}
  for line in io.lines(file) do
    lines[#lines + 1] = line
  end
  return lines
end


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
  db:close()
end

function dbmodule.findScript(scriptName)
  local nse = {}
  local db= connectDB()
  for row in db:nrows("select name from scripts where name like '%"..scriptName.."%'") do
    table.insert(nse,row.name)
  end
  if #nse > 0 then
    print('\27[1m \27[36m'..helper.banner()..'\27[21m \27[0m')
    print("\nTotal Scripts Found "..#nse.."\n")
    for k,v in ipairs(nse) do
      print('\27[92m'..k.." "..v..'\27[0m')
    end
    io.write('\nDo yo want more info about any script, choose the script using id [1-'..#nse..'] ')
    local option = io.read("*n")
    if nse[option]  then
      print("\n")
      -- tests the functions above
      local file = config.scriptsPath..nse[option]
      local lines = lines_from(file)
      for k,v in pairs(lines) do
       local i = string.find(v, "license")
       if not i then
         print('\27[96m'..v..'\27[0m')
       else
        break
       end
      end
    end
  else
    print("Not Results Found\n")
    io.write("Do you want search again? [y/n]: ")
    local action = io.read()
    if action == 'y' then
      io.write("Enter the name of the script: ")
      findScript(action)
    end
  end
end


return dbmodule
