#!/usr/bin/env python3

import sys

# This runs before the other imports, so an old Python gets this message and not an unrelated error
if sys.version_info < (3, 12):  # noqa: UP036 - ruff assumes 3.12, but this runs on whatever Python starts it
  sys.exit("Error: NSEarch requires Python 3.12 or later")

import os
import re

import i18n


def configureI18n():
  currentLocale = os.environ.get("LANG", "en")
  currentLocale = re.split(r"[_.]", currentLocale)[0]
  i18n.load_path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'i18n'))  # type: ignore[attr-defined]  # python-i18n sets these at runtime
  i18n.set("fallback", "en")  # type: ignore[attr-defined]  # python-i18n sets these at runtime
  i18n.set("locale", currentLocale)  # type: ignore[attr-defined]  # python-i18n sets these at runtime

if sys.platform == "win32":
  configureI18n()

import console
import dbmodule
import helper

# Main action
if __name__ == '__main__':
  if sys.platform != "win32":
    configureI18n()

  print(console.banner)
  if not os.path.isfile(dbmodule.dbname):
    dbmodule.initSetup()
  else:
    dbmodule.updateApp()

  helper.clearScreen()
  console_instance = console.Console()
  try:
    console_instance.cmdloop()
  except KeyboardInterrupt:
    console_instance.postloop()
