import sqlite3 as lite
import sys
import yaml
import i18n

stream = open("config.yaml", 'r')
item = yaml.load(stream)

dbname = item["config"]["scriptdb"]
categories = item["config"]["categories"]
filePath = item["config"]["filePath"]
fileBackup = item["config"]["fileBackup"]
scriptsPath = item["config"]["scriptsPath"]
lastresults = {};

def initSetup():
  print i18n.t("setup.create_db")+" "+dbname
  db = lite.connect(dbname)
  cursor = db.cursor()
  # Create Script Table
  cursor.execute('''
    create table scripts(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,name TEXT NOT NULL,
    author TEXT NULL)
  ''')
  print i18n.t("setup.create_script_table")
  db.commit()
  # Create Categories Table
  cursor.execute('''create table categories(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
     name TEXT NOT NULL)
  ''')
  print i18n.t("setup.create_category_table")
  db.commit()
  # Create Script/Category Table
  cursor.execute('''create table script_category(
    id_category INTEGER NOT NULL,
    id_script INETGER NOT NULL)
  ''')
  print i18n.t("setup.create_category_script_table")
  db.commit()
  print i18n.t("setup.upload_categories")
  for category in categories:
    cursor.execute('''
      INSERT INTO categories (name) VALUES (?)
      ''',(category,))
    db.commit()
  db.close()

  updateApp()

#update app if the db exists
def updateApp():
  print i18n.t("setup.update_db")+" "+dbname
  db = lite.connect(dbname)
  cursor = db.cursor()
  # Create Favorite Table
  cursor.execute('''
    create table if not exists favorites (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,name TEXT NOT NULL UNIQUE,
    ranking TEXT NOT NULL)
  ''')
  db.commit()
  db.close()

# Insert each Script and Author
def insertScript(script,author):
  db = lite.connect(dbname)
  db.text_factory = str
  cursor = db.cursor()
  cursor.execute('''
    Insert into scripts (name,author) values (?,?)
    ''',(script,author,))
  db.commit()
  db.close()
  return cursor.lastrowid

#Insert the scripts_id and categories_id
def insertScriptCategory(scriptid,categoryid):
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute('''
    Insert into script_category (id_category,id_script) values (?,?)
    ''',(categoryid,scriptid,))
  db.commit()
  db.close()


#get all scripts
def searchAll():
  db = lite.connect(dbname)
  cursor = db.cursor()
  cursor.execute("select id, name from scripts ")
  return __fetchScript(cursor.fetchall(),True)
  db.close()

#set script as a favorite
def createFavorite(**kwargs):
  if kwargs is not None:
    script = " "
    ranking = " "
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
    db.close()

#update favorite row
def updateFavorite(**kwargs):
  if kwargs is not None:
    sql = ""
    db = lite.connect(dbname)
    cursor = db.cursor()
    if kwargs.has_key("name") and kwargs.has_key("newname") and kwargs.has_key("newranking"):
      script = kwargs["name"]
      newname = kwargs["newname"]
      newranking = kwargs["newranking"]
      sql = '''DELETE FROM favorites WHERE name=?''',(script,)
    elif kwargs.has_key("name") and kwargs.has_key("newname"):
      script = kwargs["name"]
      newname = kwargs["newname"]
      sql = ''' '''
    elif kwargs.has_key("name") and kwargs.has_key("newranking"):
      script = kwargs["name"]
      newranking = kwargs["newranking"]
      sql = ''' '''
    else:
      print "Bad Params"
    cursor.execute(sql)
    db.commit()
    db.close()

#delete script values
def deleteFavorite(**kwargs):
  if kwargs is not None:
    db = lite.connect(dbname)
    db.text_factory = str
    cursor = db.cursor()
    if kwargs.has_key("name"):
      script = kwargs["name"]
      cursor.execute('''
        DELETE FROM favorites WHERE name=?
        ''',(script,))
      db.commit()
      db.close()
    else:
      print "Bad Params"


# Functions for all queries
def searchByCriterial(**kwargs):
  if kwargs is not None:
    sql = ""
    db = lite.connect(dbname)
    cursor = db.cursor()
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
    db.close()


# get favs scripts filter
def getFavorites(**kwargs):
  if kwargs is not None:
    sql = ""
    db = lite.connect(dbname)
    cursor = db.cursor()
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
    db.close()

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