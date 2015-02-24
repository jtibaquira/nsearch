import sqlite3 as lite
import sys
import yaml
import i18n
import hashlib
import shutil
import os

stream = open("config.yaml", 'r')
item = yaml.load(stream)

dbname = item["config"]["scriptdb"]
categories = item["config"]["categories"]
filePath = item["config"]["filePath"]
fileBackup = item["config"]["fileBackup"]
scriptsPath = item["config"]["scriptsPath"]
currentChecksum = item["config"]["checksum"]

lastresults = {};

def initSetup():
  print i18n.t("setup.create_db")+" "+dbname
  db = None
  try:
    cursor = __dbconnect()['cursor']
    # Create Script Table
    cursor.execute('''
      create table if not exists scripts(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,name TEXT NOT NULL,
      author TEXT NULL)
    ''')
    print i18n.t("setup.create_script_table")
    # Create Categories Table
    cursor.execute('''create table if not exists categories(
      id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
       name TEXT NOT NULL)
    ''')
    print i18n.t("setup.create_category_table")
    # Create Script/Category Table
    cursor.execute('''create table if not exists script_category(
      id_category INTEGER NOT NULL,
      id_script INETGER NOT NULL)
    ''')
    print i18n.t("setup.create_category_script_table")
    print i18n.t("setup.upload_categories")
    for category in categories:
      cursor.execute('''
        INSERT INTO categories (name) VALUES (?)
        ''',(category,))
      # Create Favorite Table
    print i18n.t("setup.create_favorites_table")
    cursor.execute('''
      create table if not exists favorites (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,name TEXT NOT NULL UNIQUE,
      ranking TEXT NOT NULL)
    ''')
    __dbconnect()['db'].commit()
    setData()
    createBackUp()
  except Exception, e:
    print "Error %s:" % e.args[0]
    sys.exit(1)
  finally:
    if __dbconnect()['db']:
      __dbconnect()['db'].close()

#create file backups
def createBackUp():
  print i18n.t("setup.create_backup")
  shutil.copy2(filePath, fileBackup)
  if os.path.isfile(fileBackup):
    print i18n.t("setup.create_backup_ok")
  else:
    print i18n.t("setup.create_backup_error")

#insert data into the tables
def setData():
  scriptFile = open(filePath,'r')
  for line in scriptFile:
    line = line.replace('Entry { filename = "',"").replace('", categories = { "',',"').replace('", } }','"').replace('", "','","')
    for i, j in enumerate(categories):
      line = line.replace('"'+j+'"',str(i+1))
    newarray = line.split(",")
    for key,value in enumerate(newarray):
      if value == newarray[0]:
        author = None
        currentScript = open(scriptsPath+value,'r')
        for line in currentScript:
          if line.startswith("author"):
            author = line.replace('author = "',"").replace('"',',"').replace('[[',"").replace(',"',"").replace("author =","Brandon Enright <bmenrigh@ucsd.edu>, Duane Wessels <wessels@dns-oarc.net>")
        lastrowid = insertScript(value,author)
        currentScript.close()
      else:
        insertScriptCategory(lastrowid,value)
  scriptFile.close()

#update app if the db exists
def updateApp():
  print i18n.t("setup.checking_db")+" "+dbname
  db = None
  try:
    cursor = __dbconnect()['cursor']
    # Create Favorite Table
    cursor.execute('''
      create table if not exists favorites (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,name TEXT NOT NULL UNIQUE,
      ranking TEXT NOT NULL)
    ''')
    if hashlib.md5(open(filePath, 'rb').read()).hexdigest() == currentChecksum:
      print i18n.t("setup.db_is_update")+" "+dbname
    else:
      print i18n.t("setup.update_db")
      cursor.executescript('''
        DROP TABLE IF EXISTS scripts;
        DELETE FROM SQLITE_SEQUENCE WHERE name='scripts';
        DROP TABLE IF EXISTS categories;
        DELETE FROM SQLITE_SEQUENCE WHERE name='categories';
        DROP TABLE IF EXISTS script_category;
        DELETE FROM SQLITE_SEQUENCE WHERE name='script_category';
        ''')
      __dbconnect()['db'].commit()
      __dbconnect()['db'].close()
      initSetup()
  except Exception, e:
    print "Error %s:" % e.args[0]
  finally:
    if __dbconnect()['db']:
      __dbconnect()['db'].close()


# Insert each Script and Author
def insertScript(script,author):
  db = None
  try:
    db = lite.connect(dbname)
    db.text_factory = str
    cursor = db.cursor()
    cursor.execute('''
    Insert into scripts (name,author) values (?,?)
    ''',(script,author,))
    db.commit()
    return cursor.lastrowid
  except Exception, e:
    if con:
      con.rollback()
    print "Error %s:" % e.args[0]
  finally:
    if db:
      db.close()

#Insert the scripts_id and categories_id
def insertScriptCategory(scriptid,categoryid):
  cursor = __dbconnect()['cursor']
  cursor.execute('''
    Insert into script_category (id_category,id_script) values (?,?)
    ''',(categoryid,scriptid,))
  __dbconnect()['db'].commit()
  __dbconnect()['db'].close()


#get all scripts
def searchAll():
  db= None
  try:
    cursor = __dbconnect()['cursor']
    cursor.execute("select id, name from scripts ")
    return __fetchScript(cursor.fetchall(),True)
  except Exception, e:
    print "Error %s:" % e.args[0]
  finally:
    if __dbconnect()['db']:
      __dbconnect()['db'].close()

#set script as a favorite
def createFavorite(**kwargs):
  if kwargs is not None:
    script= None
    ranking= None
    db = None
    try:
      db = lite.connect(dbname)
      db.text_factory = str
      cursor = db.cursor()
      if kwargs.has_key("name") and kwargs.has_key("ranking"):
        script = kwargs["name"]
        ranking = kwargs["ranking"]
      elif kwargs.has_key("name"):
        script = kwargs["name"]
        ranking = "normal"
      else:
        print "Bad Params"
      cursor.execute('''
        Insert into favorites (name,ranking) values (?,?)
        ''',(script,ranking,))
      db.commit()
      if cursor.rowcount == 1:
        print "[+] "+script+" "+i18n.t("setup.add_fav_ok")
    except Exception, e:
      print "[-] "+script+" "+i18n.t("setup.add_fav_error")
    finally:
      if db:
        db.close()

#update favorite row
def updateFavorite(**kwargs):
  if kwargs is not None:
    sql = None
    cursor = __dbconnect()['cursor']
    if kwargs.has_key("name") and kwargs.has_key("newname") and kwargs.has_key("newranking"):
      script = kwargs["name"]
      newname = kwargs["newname"]
      newranking = kwargs["newranking"]
      sql = ''' UPDATE favorites SET name=?, ranking=? WHERE name=?''', (newname, newranking, name,)
    elif kwargs.has_key("name") and kwargs.has_key("newname"):
      script = kwargs["name"]
      newname = kwargs["newname"]
      sql = ''' UPDATE favorites SET name=? WHERE name=?''', (newname, name,)
    elif kwargs.has_key("name") and kwargs.has_key("newranking"):
      script = kwargs["name"]
      newranking = kwargs["newranking"]
      sql = ''' UPDATE favorites SET ranking=? WHERE name=?''', (newranking, name,)
    else:
      print "Bad Params"
    cursor.execute(sql)
    __dbconnect()['db'].commit()
    __dbconnect()['db'].close()

#delete script values
def deleteFavorite(**kwargs):
  if kwargs is not None:
    db = None
    try:
      db = lite.connect(dbname)
      db.text_factory = str
      cursor = db.cursor()
      if kwargs.has_key("name"):
        script = kwargs["name"]
        cursor.execute('''
          DELETE FROM favorites WHERE name=?
          ''',(script,))
        db.commit()
      if cursor.rowcount == 1:
        print "[+] "+script+" "+i18n.t("setup.del_fav_ok")
    except Exception, e:
      print "[-] "+script+" "+i18n.t("setup.del_fav_error")
    finally:
      if db:
        db.close()


# Functions for all queries
def searchByCriterial(**kwargs):
  if kwargs is not None:
    sql = None
    cursor = __dbconnect()['cursor']
    if kwargs.has_key("name") and kwargs.has_key("category") and kwargs.has_key("author"):
      script = kwargs["name"]
      category = kwargs["category"]
      author = kwargs["author"]
      sql= "select scripts.name from scripts, categories, script_category where categories.name like '%"+category+"%' and scripts.name like '%"+script+"%' and scripts.author like '%"+author+"%' and scripts.id=script_category.id_script and categories.id=script_category.id_category "
    elif kwargs.has_key("name") and kwargs.has_key("category"):
      script = kwargs["name"]
      category = kwargs["category"]
      sql= "select scripts.name from scripts, categories, script_category where categories.name like '%"+category+"%' and scripts.name like '%"+script+"%' and  scripts.id=script_category.id_script and categories.id=script_category.id_category "
    elif kwargs.has_key("name") and kwargs.has_key("author"):
      author = kwargs["author"]
      script = kwargs["name"]
      sql= "select name from scripts where name like '%"+script+"%' and author like '%"+author+"%'"
    elif kwargs.has_key("name"):
      script = kwargs["name"]
      sql= "select name from scripts where name like '%"+script+"%'"
    elif kwargs.has_key("category"):
      category = kwargs["category"]
      sql= "select scripts.name from scripts, categories, script_category where categories.name like '%"+category+"%' and scripts.id=script_category.id_script and categories.id=script_category.id_category"
    elif kwargs.has_key("author"):
      author = kwargs["author"]
      sql= "select name from scripts where author like '%"+author+"%'"
    else:
      print "Bad Params"
    cursor.execute(sql)
    return __fetchScript(cursor.fetchall())
    __dbconnect()['db'].close()


# get favs scripts filter
def getFavorites(**kwargs):
  if kwargs is not None:
    sql = None
    cursor = __dbconnect()['cursor']
    if kwargs.has_key("name") and kwargs.has_key("ranking"):
      script = kwargs["name"]
      ranking = kwargs["ranking"]
      sql= "select scripts.name from scripts, categories, script_category where categories.name like '%"+category+"%' and scripts.name like '%"+script+"%' and  scripts.id=script_category.id_script and categories.id=script_category.id_category "
    elif kwargs.has_key("name"):
      script = kwargs["name"]
      sql= "select name from favorites where name like '%"+script+"%'"
    else:
      print "Bad Params"
    cursor.execute(sql)
    return __fetchScript(cursor.fetchall())
    __dbconnect()['db'].close()

# Connection to the databases
def __dbconnect():
  db = lite.connect(dbname)
  return {'cursor':db.cursor(), 'db':db}

# private function to fetch all results into a dic
def __fetchScript(fetchall,total=False):
  fetchlist = {};
  if total:
    for row in fetchall:
      fetchlist.update({row[0]:row[1]})
  else:
    i = 1
    for row in fetchall:
      fetchlist.update({i:row[0]})
      i = i+1
  return fetchlist