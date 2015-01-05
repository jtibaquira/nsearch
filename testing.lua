#!/usr/bin/env lua

local movie = "B.A.Pass 2013 Hindi 720p DvDRip CROPPED AAC x264 RickyKT"
movie = movie:gsub("%S+", {["2013"] = "", ["Hindi"] = "", ["720p"] = "",
                       ["DvDRip"] = "", ["CROPPED"] = "", ["AAC"] = "",
                       ["x264"] = "", ["RickyKT"] = ""})

print(movie)