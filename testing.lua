#!/usr/bin/env lua

local config = require "config"
local dbmodule = require "dbmodule"
scriptdb = config.scriptdb

dbmodule.InitSetup( scriptdb, "wc")
