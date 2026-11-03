import os
import sys
import tempfile

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

CATEGORIES = ["auth", "default", "safe", "vuln"]

# dbmodule reads its config on import, so this must exist before it is imported
bootstrap = tempfile.mkdtemp()
os.environ["NSEARCH_CONFIG"] = os.path.join(bootstrap, "config.yaml")
with open(os.environ["NSEARCH_CONFIG"], "w", encoding="utf-8") as f:
  yaml.safe_dump({"config": {"scriptdb": os.path.join(bootstrap, "boot.sqlite3"), "categories": CATEGORIES,
    "filePath": os.path.join(bootstrap, "script.db"), "fileBackup": os.path.join(bootstrap, "backup.db"),
    "scriptsPath": bootstrap + "/", "checksum": ""}}, f)

import dbmodule
import i18n

i18n.load_path.append(os.path.join(ROOT, "i18n"))
i18n.set("fallback", "en")
i18n.set("locale", "en")

SCRIPTS = {
  "http-title.nse": 'description = [[\nChecks localhost titles.\n]]\nlocal shortport = require "shortport"\nauthor = "Diman Todorov"\n',
  "http-vuln.nse": 'author = {"Paulino Calderon", "Paul Amar"}\n',
  "dns-txid.nse": 'author = [[\nScript: Brandon Enright\nDuane Wessels\n]]\n',
}
SCRIPT_DB = (
  'Entry { filename = "http-title.nse", categories = { "default", "safe", } }\n'
  'Entry { filename = "http-vuln.nse", categories = { "vuln", "unknown", } }\n'
  'Entry { filename = "dns-txid.nse", categories = { "safe", } }\n'
  'Entry { filename = "missing.nse", categories = { "auth", } }\n'
  'this line is not an entry\n'
)

@pytest.fixture
def db(tmp_path, monkeypatch):
  scripts = tmp_path / "scripts"
  scripts.mkdir()
  for name, content in SCRIPTS.items():
    (scripts / name).write_text(content, encoding="utf-8")
  (scripts / "script.db").write_text(SCRIPT_DB, encoding="utf-8")
  config = tmp_path / "config.yaml"
  item = {"config": {"scriptdb": str(tmp_path / "test.sqlite3"), "categories": CATEGORIES,
    "filePath": str(scripts / "script.db"), "fileBackup": str(tmp_path / "backup.db"),
    "scriptsPath": str(scripts) + "/", "checksum": ""}}
  config.write_text(yaml.safe_dump(item), encoding="utf-8")
  monkeypatch.setattr(dbmodule, "item", item)
  monkeypatch.setattr(dbmodule, "config_path", str(config))
  monkeypatch.setattr(dbmodule, "dbname", item["config"]["scriptdb"])
  monkeypatch.setattr(dbmodule, "categories", CATEGORIES)
  monkeypatch.setattr(dbmodule, "filePath", item["config"]["filePath"])
  monkeypatch.setattr(dbmodule, "fileBackup", item["config"]["fileBackup"])
  monkeypatch.setattr(dbmodule, "scriptsPath", item["config"]["scriptsPath"])
  monkeypatch.setattr(dbmodule, "currentChecksum", "")
  monkeypatch.setattr(dbmodule, "lastresults", {})
  monkeypatch.setattr(dbmodule, "lastresultsFav", False)
  dbmodule.initSetup()
  return dbmodule
