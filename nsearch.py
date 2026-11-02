#!/usr/bin/env python3

import console

import dbmodule
import helper
import i18n
import os
import re

# Main action
if __name__ == '__main__':

  currentLocale = os.environ.get("LANG", "en")
  currentLocale = re.split(r"[_.]", currentLocale)[0]
  i18n.load_path.append(os.path.join(dbmodule.BASE_DIR, 'i18n'))
  i18n.set("fallback", "en")
  i18n.set("locale", currentLocale)

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
