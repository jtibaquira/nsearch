-- module for initial setup

local config = require "config"
local categoryList = config.categories
local filePath = config.filePath
local dbmodule = require "dbmodule"

local setup = {}

function setup.file_exists(file)
  local f = io.open(file, "rb")
  if f then f:close() end
  return f ~= nil
end

-- get all lines from a file, returns an empty
-- list/table if the file does not exist
function lines_from(file)
  if not setup.file_exists(file) then print "File don't exist" os.exit() end
  lines = {}
  for line in io.lines(file) do
    lines[#lines + 1] = line
  end
  return lines
end

-- tests the functions above
local file = filePath
local lines = lines_from(file)

-- create a script.db backups
function createBackup()
  outfile = io.open(config.fileBackup, "w")
  for k,v in pairs(lines) do
    outfile:write(v.."\n")
  end
  outfile:close()
  if not setup.file_exists(config.fileBackup) then
    print "the backup can not created"
  else
    print "backup succesfull"
  end
end

function setup.install(banner)
  print('\27[1m \27[36m'..banner..'\27[21m \27[0m')
  dbmodule.InitSetup("wc")
  local t ={}
  local id_script = 0
  for k,v in ipairs(lines) do
    v = v:gsub('%Entry { filename = "',""):gsub('", categories = { "',',"'):gsub('", } }','"'):gsub('", "','","')
    for i,c in ipairs(categoryList) do
      v = v:gsub('"'..c..'"',i)
    end
    for a in string.gmatch(v,"([^,]+)") do
      table.insert(t,a)
    end
    for key,value in ipairs(t) do
      if t[1] == value then
        local val = {value}
        id_script = dbmodule.InsertScript(val,"scripts")
      else
        dbmodule.InsertCategory(id_script,value)
      end
    end
    t = {}
  end
  createBackup()
end
return setup
