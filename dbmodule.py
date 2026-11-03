import hashlib
import i18n
import os
import re
import shutil
import sqlite3 as lite
import sys
import tempfile
import yaml

from contextlib import closing
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.environ.get("NSEARCH_CONFIG", os.path.join(BASE_DIR, "config.yaml"))

try:
  with open(config_path, 'r', encoding="utf-8") as stream:
    item = yaml.safe_load(stream)
  dbname = os.path.join(BASE_DIR, item["config"]["scriptdb"])
  categories = list(item["config"]["categories"])
  filePath = item["config"]["filePath"]
  fileBackup = os.path.join(BASE_DIR, item["config"]["fileBackup"])
  scriptsPath = item["config"]["scriptsPath"]
  currentChecksum = item["config"].get("checksum", "")
except FileNotFoundError:
  print("Error: config.yaml not found. Run 'bash install.sh' or copy config.yaml.example to config.yaml")
  sys.exit(1)
except (yaml.YAMLError, KeyError, TypeError):
  print("Error: config.yaml is not valid. Run 'bash install.sh' or compare it with config.yaml.example")
  sys.exit(1)

lastresults = {}
lastresultsFav = False

def sanitize(text):
  return re.sub(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", "?", str(text))

def __fileHash():
  with open(filePath, 'rb') as scriptFile:
    return hashlib.sha256(scriptFile.read()).hexdigest()

# Rebuild the script tables in one transaction; favorites are never dropped
def __buildDb():
  conn = lite.connect(dbname)
  try:
    cursor = conn.cursor()
    cursor.execute("BEGIN")
    for table in ("script_category", "categories", "scripts"):
      cursor.execute("DROP TABLE IF EXISTS " + table)
    print(i18n.t("setup.create_script_table"))
    cursor.execute('''create table scripts(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
      name TEXT NOT NULL, author TEXT NULL)''')
    print(i18n.t("setup.create_category_table"))
    cursor.execute('''create table categories(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
      name TEXT NOT NULL)''')
    print(i18n.t("setup.create_category_script_table"))
    cursor.execute('''create table script_category(id_category INTEGER NOT NULL,
      id_script INTEGER NOT NULL)''')
    cursor.execute("create index idx_script_category_script on script_category(id_script)")
    cursor.execute("create index idx_script_category_category on script_category(id_category)")
    print(i18n.t("setup.create_favorites_table"))
    cursor.execute('''create table if not exists favorites(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
      name TEXT NOT NULL UNIQUE, ranking TEXT NOT NULL)''')
    print(i18n.t("setup.upload_categories"))
    cursor.executemany("INSERT INTO categories (name) VALUES (?)", [(category,) for category in categories])
    setData(cursor)
    conn.commit()
  except Exception:
    conn.rollback()
    raise
  finally:
    conn.close()

def initSetup():
  print(i18n.t("setup.create_db") + " " + dbname)
  try:
    __buildDb()
    createBackUp()
    __updateHash(currentChecksum, __fileHash())
  except (OSError, lite.Error) as e:
    print("Error %s:" % e)
    sys.exit(1)

# Create a backup of script.db
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

# Update the app if the database exists
def updateApp():
  print(i18n.t("setup.checking_db") + " " + dbname)
  try:
    newhash = __fileHash()
    if newhash == currentChecksum:
      print(i18n.t("setup.db_is_update") + " " + dbname)
      return
    print(i18n.t("setup.update_db"))
    __buildDb()
    __updateHash(currentChecksum, newhash)
  except (OSError, lite.Error) as e:
    print("Error %s:" % e)

# Insert a script and its author
def insertScript(cursor, script, author):
  cursor.execute("INSERT INTO scripts (name, author) VALUES (?, ?)", (script, author))
  return cursor.lastrowid

# Insert the script and category ids
def insertScriptCategory(cursor, scriptid, categoryid):
  cursor.execute("INSERT INTO script_category (id_category, id_script) VALUES (?, ?)", (categoryid, scriptid))
  sys.stdout.write("#")
  sys.stdout.flush()

# Get all scripts
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

# Set a script as a favorite
def createFavorite(**kwargs):
  if "name" not in kwargs:
    print(i18n.t("setup.bad_params"))
    return
  script = kwargs["name"]
  conn = lite.connect(dbname)
  try:
    with conn:
      conn.execute("INSERT INTO favorites (name, ranking) VALUES (?, ?)", (script, kwargs.get("ranking", "normal")))
    print("[+] " + sanitize(script) + " " + i18n.t("setup.add_fav_ok"))
  except lite.IntegrityError:
    print("[-] " + sanitize(script) + " " + i18n.t("setup.add_fav_error"))
  finally:
    conn.close()

# Update a favorite
def updateFavorite(**kwargs):
  fields, params = [], []
  for column, key in (("name", "newname"), ("ranking", "newranking")):
    if key in kwargs:
      fields.append(column + "=?")
      params.append(kwargs[key])
  if "name" not in kwargs or not fields:
    print(i18n.t("setup.bad_params"))
    return
  script = kwargs["name"]
  conn = lite.connect(dbname)
  try:
    with conn:
      updated = conn.execute("UPDATE favorites SET " + ", ".join(fields) + " WHERE name=?", params + [script]).rowcount
    if updated:
      print("[+] " + sanitize(script) + " " + i18n.t("setup.update_fav_ok"))
    else:
      print("[-] " + sanitize(script) + " " + i18n.t("setup.update_fav_error"))
  except lite.IntegrityError:
    print("[-] " + sanitize(script) + " " + i18n.t("setup.update_fav_error"))
  finally:
    conn.close()

# Delete a favorite
def deleteFavorite(**kwargs):
  if "name" not in kwargs:
    print(i18n.t("setup.bad_params"))
    return
  script = kwargs["name"]
  conn = lite.connect(dbname)
  try:
    with conn:
      deleted = conn.execute("DELETE FROM favorites WHERE name=?", (script,)).rowcount
    if deleted:
      print("[+] " + sanitize(script) + " " + i18n.t("setup.del_fav_ok"))
    else:
      print("[-] " + sanitize(script) + " " + i18n.t("setup.del_fav_error"))
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


# Get favorites, with optional filters
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

# Private function to fetch all results into a dict
def __fetchScript(fetchall, total=False):
  fetchlist = {}
  if total:
    for row in fetchall:
      fetchlist.update({row["id"]: {"name": row["name"], "ranking": row["ranking"]}})
  else:
    for row in fetchall:
      fetchlist.update({row["id"]: {"name": row["name"], "author": row["author"]}})
  return fetchlist


def __updateHash(oldhash, newhash):
  item["config"]["categories"] = categories
  item["config"]["checksum"] = newhash
  fd, tmppath = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(config_path)))
  try:
    with os.fdopen(fd, 'w', encoding="utf-8") as f:
      yaml.safe_dump(item, f)
    os.replace(tmppath, config_path)
  except Exception:
    os.remove(tmppath)
    raise

# Workflow tables are kept when the script tables are rebuilt
WORKFLOW_SCHEMA = """
  create table if not exists workflow_runs(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    workflow TEXT NOT NULL, target TEXT NOT NULL, status TEXT NOT NULL,
    started_at TEXT NOT NULL, finished_at TEXT NULL);
  create table if not exists workflow_stages(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    run_id INTEGER NOT NULL, position INTEGER NOT NULL, name TEXT NOT NULL,
    arguments TEXT NULL, status TEXT NOT NULL, UNIQUE(run_id, position));
  create table if not exists workflow_hosts(run_id INTEGER NOT NULL, address TEXT NOT NULL,
    hostname TEXT NULL, state TEXT NOT NULL, PRIMARY KEY(run_id, address));
  create table if not exists workflow_services(run_id INTEGER NOT NULL, address TEXT NOT NULL,
    protocol TEXT NOT NULL, port INTEGER NOT NULL, state TEXT NOT NULL, service TEXT NULL,
    product TEXT NULL, version TEXT NULL, PRIMARY KEY(run_id, address, protocol, port));
  create table if not exists workflow_findings(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    run_id INTEGER NOT NULL, stage TEXT NOT NULL, address TEXT NOT NULL, port INTEGER NULL,
    script TEXT NOT NULL, output TEXT NOT NULL);
"""

def __workflowConnect():
  conn = lite.connect(dbname)
  conn.row_factory = lite.Row
  conn.executescript(WORKFLOW_SCHEMA)
  return conn

def __now():
  return datetime.now(timezone.utc).isoformat(timespec="seconds")

# Create a workflow run and its pending stages
def createRun(workflow, target, stages):
  with closing(__workflowConnect()) as conn, conn:
    runId = conn.execute("INSERT INTO workflow_runs (workflow, target, status, started_at) VALUES (?, ?, 'running', ?)",
      (workflow, target, __now())).lastrowid
    conn.executemany("INSERT INTO workflow_stages (run_id, position, name, arguments, status) VALUES (?, ?, ?, ?, 'pending')",
      [(runId, position, stage["name"], stage.get("arguments")) for position, stage in enumerate(stages)])
    return runId

def setStageStatus(runId, position, status):
  with closing(__workflowConnect()) as conn, conn:
    conn.execute("UPDATE workflow_stages SET status=? WHERE run_id=? AND position=?", (status, runId, position))

def setRunStatus(runId, status):
  with closing(__workflowConnect()) as conn, conn:
    conn.execute("UPDATE workflow_runs SET status=?, finished_at=? WHERE id=?", (status, __now(), runId))

# Save everything found by one stage in a single transaction
def saveStageResults(runId, stage, hosts, services, findings):
  with closing(__workflowConnect()) as conn, conn:
    conn.executemany("""INSERT INTO workflow_hosts (run_id, address, hostname, state) VALUES (?, ?, ?, ?)
      ON CONFLICT(run_id, address) DO UPDATE SET state=excluded.state,
      hostname=COALESCE(NULLIF(excluded.hostname, ''), hostname)""",
      [(runId, host["address"], host["hostname"], host["state"]) for host in hosts])
    conn.executemany("""INSERT INTO workflow_services (run_id, address, protocol, port, state, service, product, version)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(run_id, address, protocol, port) DO UPDATE SET state=excluded.state,
      service=COALESCE(NULLIF(excluded.service, ''), service),
      product=COALESCE(NULLIF(excluded.product, ''), product),
      version=COALESCE(NULLIF(excluded.version, ''), version)""",
      [(runId, item["address"], item["protocol"], item["port"], item["state"], item["service"], item["product"], item["version"])
        for item in services])
    conn.executemany("INSERT INTO workflow_findings (run_id, stage, address, port, script, output) VALUES (?, ?, ?, ?, ?, ?)" +
      " ON CONFLICT DO NOTHING", [(runId, stage, item["address"], item["port"], item["script"], item["output"]) for item in findings])

def getLiveHosts(runId):
  with closing(__workflowConnect()) as conn:
    return [row["address"] for row in conn.execute(
      "SELECT address FROM workflow_hosts WHERE run_id=? AND state='up' ORDER BY address", (runId,))]

def addRunHost(runId, host_info):
  """Add a host to the workflow run. host_info is {'address': str, 'state': str}"""
  with closing(__workflowConnect()) as conn:
    conn.execute(
      "INSERT INTO workflow_hosts (run_id, address, state) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
      (runId, host_info["address"], host_info.get("state", "unknown")))

# Open ports per host, optionally only for the given service names
def getOpenPorts(runId, services=None):
  sql = "SELECT address, port FROM workflow_services WHERE run_id=? AND state='open'"
  params = [runId]
  if services:
    sql += " AND service IN (" + ", ".join("?" for _ in services) + ")"
    params += services
  ports = {}
  with closing(__workflowConnect()) as conn:
    for row in conn.execute(sql + " ORDER BY address, port", params):
      ports.setdefault(row["address"], []).append(row["port"])
  return ports

def getRuns():
  with closing(__workflowConnect()) as conn:
    return [dict(row) for row in conn.execute("SELECT * FROM workflow_runs ORDER BY id DESC")]

def getRun(runId):
  with closing(__workflowConnect()) as conn:
    run = conn.execute("SELECT * FROM workflow_runs WHERE id=?", (runId,)).fetchone()
    if run is None:
      return None
    details = {"run": dict(run)}
    for key, sql in (
      ("stages", "SELECT * FROM workflow_stages WHERE run_id=? ORDER BY position"),
      ("hosts", "SELECT * FROM workflow_hosts WHERE run_id=? ORDER BY address"),
      ("services", "SELECT * FROM workflow_services WHERE run_id=? AND state='open' ORDER BY address, port"),
      ("findings", "SELECT * FROM workflow_findings WHERE run_id=? ORDER BY id")):
      details[key] = [dict(row) for row in conn.execute(sql, (runId,))]
    return details

# Script names mapped to their categories
def scriptCategories():
  sql = """SELECT scripts.name AS script, categories.name AS category FROM scripts
    JOIN script_category ON scripts.id = script_category.id_script
    JOIN categories ON categories.id = script_category.id_category"""
  scripts = {}
  with closing(lite.connect(dbname)) as conn:
    for script, category in conn.execute(sql):
      scripts.setdefault(re.sub(r"\.nse$", "", script), set()).add(category)
  return scripts
