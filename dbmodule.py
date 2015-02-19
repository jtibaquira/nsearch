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



def searchByCriterial(**kwargs):
  if kwargs is not None:
    db = lite.connect(dbname)
    cursor = db.cursor()
    if kwargs.has_key("name") and kwargs.has_key("category") and kwargs.has_key("author"):
      author = kwargs["author"]
      script = kwargs["name"]
      category = kwargs["category"]
      cursor = db.execute("select scripts.name from scripts, categories, script_category where categories.name like '%"+category+"%' and scripts.name like '%"+script+"%' and scripts.author like '%"+author+"%' and scripts.id=script_category.id_script and categories.id=script_category.id_category ")
    elif kwargs.has_key("name") and kwargs.has_key("category"):
      script = kwargs["name"]
      category = kwargs["category"]
      cursor = db.execute("select scripts.name from scripts, categories, script_category where categories.name like '%"+category+"%' and scripts.name like '%"+script+"%' and  scripts.id=script_category.id_script and categories.id=script_category.id_category ")
    elif kwargs.has_key("name") and kwargs.has_key("author"):
      author = kwargs["author"]
      script = kwargs["name"]
      cursor.execute("select name from scripts where name like '%"+script+"%' and author like '%"+author+"%'")
    elif kwargs.has_key("name"):
      script = kwargs["name"]
      cursor.execute("select name from scripts where name like '%"+script+"%'")
    elif kwargs.has_key("category"):
      category = kwargs["category"]
      cursor.execute("select scripts.name from scripts, categories, script_category where categories.name like '%"+category+"%' and scripts.id=script_category.id_script and categories.id=script_category.id_category")
    elif kwargs.has_key("author"):
      author = kwargs["author"]
      cursor.execute("select name from scripts where author like '%"+author+"%'")
    else:
      print "Empty"
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