#!/usr/bin/env python

import dbmodule
from dbmodule import *
import console
from console import *
import re

banner ='\033[0;36m'+'''
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.4b  http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================
'''+'\033[0m'

# main action
if __name__ == '__main__':

  currentLocale = re.sub('[_].*','',os.environ['LANG'])
  i18n.load_path.append('i18n')
  i18n.set('locale',currentLocale) if True else i18n.set('fallback','en')

  print banner
  if not os.path.isfile(dbmodule.dbname):
    dbmodule.initSetup()
  else:
    dbmodule.updateApp()

  os.system("clear")
  console = console.Console()
  console.cmdloop()