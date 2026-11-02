import hashlib
import i18n
import os
import re
import shutil
import sqlite3 as lite
import sys
import tempfile
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.environ.get("NSEARCH_CONFIG", os.path.join(BASE_DIR, "config.yaml"))

try:
  with open(config_path, 'r', encoding="utf-8") as stream:
    item = yaml.safe_load(stream)
except FileNotFoundError:
  print("Error: config.yaml not found. Run 'sh install.sh' or copy config.yaml.example to config.yaml")
  sys.exit(1)

dbname = item["config"]["scriptdb"]
categories = item["config"]["categories"]
if isinstance(categories, dict):
  categories = list(categories.keys())
filePath = item["config"]["filePath"]
fileBackup = item["config"]["fileBackup"]
scriptsPath = item["config"]["scriptsPath"]
currentChecksum = item["config"].get("checksum", "")

lastresults = {}

def initSetup():
  print(i18n.t("setup.create_db") + " " + dbname)
  conn = lite.connect(dbname)
  try:
    with conn:
      cursor = conn.cursor()
      # Create Script Table
      cursor.execute('''
        create table if not exists scripts(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,name TEXT NOT NULL,
        author TEXT NULL)
      ''')
      print(i18n.t("setup.create_script_table"))
      # Create Categories Table
      cursor.execute('''create table if not exists categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
         name TEXT NOT NULL)
      ''')
      print(i18n.t("setup.create_category_table"))
      # Create Script/Category Table
      cursor.execute('''create table if not exists script_category(
        id_category INTEGER NOT NULL,
        id_script INTEGER NOT NULL)
      ''')
      print(i18n.t("setup.create_category_script_table"))
      print(i18n.t("setup.upload_categories"))
      for category in categories:
        cursor.execute('''
          INSERT INTO categories (name) VALUES (?)
          ''', (category,))
      # Create Favorite Table
      print(i18n.t("setup.create_favorites_table"))
      cursor.execute('''
        create table if not exists favorites (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,name TEXT NOT NULL UNIQUE,
        ranking TEXT NOT NULL)
      ''')
      setData(cursor)
  except Exception as e:
    print("Error %s:" % e.args[0])
    sys.exit(1)
  finally:
    conn.close()

#create file backups
def createBackUp():
  print("\n" + i18n.t("setup.create_backup"))
  shutil.copy2(filePath, fileBackup)
  if os.path.isfile(fileBackup):
    print(i18n.t("setup.create_backup_ok"))
  else:
    print(i18n.t("setup.create_backup_error"))

AUTHOR_RE = re.compile(r'^author\s*=\s*(\{.*?\}|\[\[.*?\]\]|.*?$)', re.M | re.S)
STRING_RE = re.compile(r'"([^"]*)"|\'([^\']*)\'|\[\[(.*?)\]\]', re.S)

def parseAuthor(content):
  match = AUTHOR_RE.search(content)
  if not match:
    return None
  names = [" ".join("".join(groups).split()) for groups in STRING_RE.findall(match.group(1))]
  return ", ".join(name for name in names if name) or None

def setData(cursor):
  categoryIds = {name: i + 1 for i, name in enumerate(categories)}
  with open(filePath, 'r', encoding="utf-8", errors="replace") as scriptFile:
    for line in scriptFile:
      match = re.search(r'filename\s*=\s*"([^"]+)"', line)
      if not match:
        continue
      name = match.group(1)
      block = re.search(r'categories\s*=\s*\{(.*?)\}', line)
      names = re.findall(r'"([^"]+)"', block.group(1)) if block else []
      author = None
      scriptPath = os.path.join(scriptsPath, name)
      if os.path.isfile(scriptPath):
        with open(scriptPath, 'r', encoding="utf-8", errors="replace") as currentScript:
          author = parseAuthor(currentScript.read())
      lastrowid = insertScript(cursor, name, author)
      for category in names:
        if category in categoryIds:
          insertScriptCategory(cursor, lastrowid, categoryIds[category])

#update app if the db exists
def updateApp():
  print(i18n.t("setup.checking_db") + " " + dbname)
  conn = lite.connect(dbname)
  try:
    with conn:
      cursor = conn.cursor()
      # Create Favorite Table
      cursor.execute('''
        create table if not exists favorites (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,name TEXT NOT NULL UNIQUE,
        ranking TEXT NOT NULL)
      ''')
      newhash = hashlib.sha256(open(filePath, 'rb').read()).hexdigest()
      if newhash == currentChecksum:
        print(i18n.t("setup.db_is_update") + " " + dbname)
      else:
        __updateHash(currentChecksum, newhash)
        print(i18n.t("setup.update_db"))
        cursor.executescript('''
          DROP TABLE IF EXISTS scripts;
          DELETE FROM SQLITE_SEQUENCE WHERE name='scripts';
          DROP TABLE IF EXISTS categories;
          DELETE FROM SQLITE_SEQUENCE WHERE name='categories';
          DROP TABLE IF EXISTS script_category;
          DELETE FROM SQLITE_SEQUENCE WHERE name='script_category';
          ''')
        setData(cursor)
  except Exception as e:
    print("Error %s:" % e.args[0])
  finally:
    conn.close()


# Insert each Script and Author
def insertScript(cursor, script, author):
  try:
    cursor.execute('''
    Insert into scripts (name,author) values (?,?)
    ''', (script, author,))
    return cursor.lastrowid
  except Exception as e:
    print("Error %s:" % e.args[0])


#Insert the scripts_id and categories_id
def insertScriptCategory(cursor, scriptid, categoryid):
  try:
    cursor.execute('''
    INSERT INTO script_category (id_category,id_script) VALUES (?,?)
    ''', (categoryid, scriptid,))
    if cursor.rowcount == 1:
      sys.stdout.flush()
      sys.stdout.write("#")
  except Exception as e:
    print("Error %s:" % e.args[0])

#get all scripts
def searchAll():
  conn = lite.connect(dbname)
  try:
    conn.row_factory = lite.Row
    cursor = conn.cursor()
    cursor.execute("select id, name, author from scripts ORDER BY name")
    return __fetchScript(cursor.fetchall())
  except Exception as e:
    print("Error %s:" % e.args[0])
  finally:
    conn.close()

#set script as a favorite
def createFavorite(**kwargs):
  script = None
  ranking = None
  conn = lite.connect(dbname)
  try:
    with conn:
      cursor = conn.cursor()
      if "name" in kwargs and "ranking" in kwargs:
        script = kwargs["name"]
        ranking = kwargs["ranking"]
      elif "name" in kwargs:
        script = kwargs["name"]
        ranking = "normal"
      else:
        print(i18n.t("setup.bad_params"))
      cursor.execute('''
        Insert into favorites (name,ranking) values (?,?)
        ''', (script, ranking,))
      if cursor.rowcount == 1:
        print("[+] " + script + " " + i18n.t("setup.add_fav_ok"))
  except lite.IntegrityError:
    print("[-] " + script + " " + i18n.t("setup.add_fav_error"))
  except Exception as e:
    print("Error %s:" % e.args[0])
  finally:
    conn.close()

#update favorite row
def updateFavorite(**kwargs):
  sql = None
  conn = lite.connect(dbname)
  try:
    with conn:
      cursor = conn.cursor()
      if "name" in kwargs and "newname" in kwargs and "newranking" in kwargs:
        script = kwargs["name"]
        newname = kwargs["newname"]
        newranking = kwargs["newranking"]
        cursor.execute('''
          UPDATE favorites SET name=?, ranking=? WHERE name=?
          ''', (newname, newranking, script,))
      elif "name" in kwargs and "newname" in kwargs:
        script = kwargs["name"]
        newname = kwargs["newname"]
        cursor.execute('''
          UPDATE favorites SET name=? WHERE name=?
          ''', (newname, script,))
      elif "name" in kwargs and "newranking" in kwargs:
        script = kwargs["name"]
        newranking = kwargs["newranking"]
        cursor.execute('''
          UPDATE favorites SET ranking=? WHERE name=?
          ''', (newranking, script,))
      else:
        print(i18n.t("setup.bad_params"))
      if cursor.rowcount == 1:
        print("[+] " + script + " " + i18n.t("setup.update_fav_ok"))
      elif cursor.rowcount == 0:
        print(i18n.t("setup.update_fav_error"))
  except Exception as e:
    print("Error %s:" % e.args[0])
    print("[-] " + script + " " + i18n.t("setup.update_fav_error"))
  finally:
    conn.close()

#delete script values
def deleteFavorite(**kwargs):
  conn = lite.connect(dbname)
  try:
    with conn:
      cursor = conn.cursor()
      if "name" in kwargs:
        script = kwargs["name"]
        cursor.execute('''
          DELETE FROM favorites WHERE name=?
          ''', (script,))
        if cursor.rowcount == 1:
          print("[+] " + script + " " + i18n.t("setup.del_fav_ok"))
        elif cursor.rowcount == 0:
          print("[-] " + script + " " + i18n.t("setup.del_fav_error"))
  except Exception as e:
    print("[-] " + script + " " + i18n.t("setup.del_fav_error"))
  finally:
    conn.close()


def searchByCriterial(**kwargs):
  conn = lite.connect(dbname)
  try:
    conn.row_factory = lite.Row
    cursor = conn.cursor()
    if "name" in kwargs and "category" in kwargs and "author" in kwargs:
      script = kwargs["name"]
      category = kwargs["category"]
      author = kwargs["author"]
      cursor.execute('''SELECT scripts.id, scripts.name, scripts.author 
                         FROM scripts JOIN categories ON categories.id=script_category.id_category 
                         JOIN script_category ON scripts.id=script_category.id_script 
                         WHERE categories.name LIKE ? AND scripts.name LIKE ? AND scripts.author LIKE ?''', 
                    ('%'+category+'%', '%'+script+'%', '%'+author+'%'))
    elif "name" in kwargs and "category" in kwargs:
      script = kwargs["name"]
      category = kwargs["category"]
      cursor.execute('''SELECT scripts.id, scripts.name, scripts.author 
                         FROM scripts JOIN categories ON categories.id=script_category.id_category 
                         JOIN script_category ON scripts.id=script_category.id_script 
                         WHERE categories.name LIKE ? AND scripts.name LIKE ?''', 
                    ('%'+category+'%', '%'+script+'%'))
    elif "name" in kwargs and "author" in kwargs:
      author = kwargs["author"]
      script = kwargs["name"]
      cursor.execute('''SELECT id, name, author FROM scripts WHERE name LIKE ? AND author LIKE ?''', 
                    ('%'+script+'%', '%'+author+'%'))
    elif "name" in kwargs:
      script = kwargs["name"]
      cursor.execute('''SELECT id, name, author FROM scripts WHERE name LIKE ?''', ('%'+script+'%',))
    elif "category" in kwargs:
      category = kwargs["category"]
      cursor.execute('''SELECT scripts.id, scripts.name, scripts.author 
                         FROM scripts JOIN script_category ON scripts.id=script_category.id_script 
                         JOIN categories ON categories.id=script_category.id_category 
                         WHERE categories.name LIKE ?''', ('%'+category+'%',))
    elif "author" in kwargs:
      author = kwargs["author"]
      cursor.execute('''SELECT id, name, author FROM scripts WHERE author LIKE ?''', ('%'+author+'%',))
    else:
      print(i18n.t("setup.bad_params"))
      return {}
    return __fetchScript(cursor.fetchall())
  finally:
    conn.close()


# get favs scripts filter
def getFavorites(**kwargs):
  conn = lite.connect(dbname)
  try:
    conn.row_factory = lite.Row
    cursor = conn.cursor()
    if "name" in kwargs and "ranking" in kwargs:
      script = kwargs["name"]
      ranking = kwargs["ranking"]
      cursor.execute("select id, name, ranking from favorites where name like ? and ranking like ?", ('%'+script+'%', '%'+ranking+'%'))
    elif "name" in kwargs:
      script = kwargs["name"]
      cursor.execute("select id, name, ranking from favorites where name like ?", ('%'+script+'%',))
    elif "ranking" in kwargs:
      ranking = kwargs["ranking"]
      cursor.execute("select id, name, ranking from favorites where ranking like ?", ('%'+ranking+'%',))
    else:
      cursor.execute("select id, name, ranking from favorites")
    return __fetchScript(cursor.fetchall(), True)
  finally:
    conn.close()

# private function to fetch all results into a dict
def __fetchScript(fetchall, total=False):
  fetchlist = {}
  if total:
    for row in fetchall:
      fetchlist.update({row["id"]: {"name": row["name"], "ranking": row["ranking"]}})
  else:
    for row in fetchall:
      fetchlist.update({row["id"]: {"name": row["name"], "author": row["author"]}})
  return fetchlist


def __updateHash(oldhash, newnhash):
  """Atomic hash update using tempfile and os.replace"""
  tmpfile = None
  try:
    fd, tmpfile = tempfile.mkstemp(dir=os.path.dirname(config_path), suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
      newconfig = {'config': {
        'scriptsPath': scriptsPath,
        'filePath': filePath,
        'fileBackup': fileBackup,
        'scriptdb': dbname,
        'categories': categories,
        'checksum': newnhash}}
      yaml.safe_dump(newconfig, f)
    os.replace(tmpfile, config_path)
  except Exception:
    if tmpfile is not None and os.path.exists(tmpfile):
      os.unlink(tmpfile)
    raise

