#!/usr/bin/env lua

--local config = require "config"
--local dbmodule = require "dbmodule"
--scriptdb = config.scriptdb

--dbmodule.InitSetup( scriptdb, "wc")
--t = {}
 --s = "http-vuln-cve2013-0156.nse|7, 14"
 --for k, v in string.gmatch(s, "(%s+)|(%s+)") do
   --t[k] = v
   --print(k,v)
 --end
local t ={}
str = 'http-vuln-cve2013-0156.nse,7,14,2,3,5'
for k in string.gmatch(str, '([^,]+)') do
  table.insert(t,k)
end
for i,v in ipairs(t) do
  if t[1] == v then
    print(v.." it's a scriptdb")
  else
    print(v.." it's a categorie")
  end
end