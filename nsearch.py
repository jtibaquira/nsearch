#!/usr/bin/env python3

import os
import re

import i18n

import console
import dbmodule
import helper

# Main action
if __name__ == '__main__':

  currentLocale = os.environ.get("LANG", "en")
  currentLocale = re.split(r"[_.]", currentLocale)[0]
  i18n.load_path.append(os.path.join(dbmodule.BASE_DIR, 'i18n'))  # type: ignore[attr-defined]  # python-i18n sets these at runtime
  i18n.set("fallback", "en")  # type: ignore[attr-defined]  # python-i18n sets these at runtime
  i18n.set("locale", currentLocale)  # type: ignore[attr-defined]  # python-i18n sets these at runtime

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
