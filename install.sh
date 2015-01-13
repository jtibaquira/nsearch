#!/bin/env bash

dbpath=$(find /usr -type f -name "script.db" 2>/dev/null)

if [[ $dbpath ]]; then
  echo $dbpath >> settings.lua
fi