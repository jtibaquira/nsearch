-- module for initial setup

local config = require "config"
local categoryList = config.categories

local dbmodule = require "dbmodule"
scriptdb = config.scriptdb
local setup = {}

function setup.install(lines)
  local t ={}
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
       dbmodule.InitSetup( scriptdb, "wc")
       print(value.." it's a scriptdb")
      else
       print(value.." it's a categorie")
      end
    end
    t = {}
  end
end
return setup
