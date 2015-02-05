import dbmodule


def process(args):
  if not args:
    for row in dbmodule.searchAll():
      print('\033[1;32m'+str(row[0])+"."+row[1]+'\033[0m')
  else:
    criterial = args.split(":")[1]
    criterial.split(" ")[0]
    if args.startswith('name:'):
      scriptlist = dbmodule.searchScript(criterial)
      for k,v in scriptlist.items():
        print('\033[1;32m'+str(k)+"."+v+'\033[0m')
    elif args.startswith("category:"):
      scriptlist = dbmodule.searchCategory(criterial)
      for k,v in scriptlist.items():
        print('\033[1;32m'+str(k)+"."+v+'\033[0m')
    else:
      print "Search all Scripts"