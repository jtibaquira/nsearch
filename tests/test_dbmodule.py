import sqlite3

import pytest
import yaml

import dbmodule

def names(results):
  return sorted(value["name"] for value in results.values())

def checksum(db):
  with open(db.config_path, encoding="utf-8") as f:
    return yaml.safe_load(f)["config"]["checksum"]

@pytest.mark.parametrize("content,expected", [
  ('author = "Jane Doe"\n', "Jane Doe"),
  ('author = {"jah", "Michael Pattrick"}\n', "jah, Michael Pattrick"),
  ('author = {\n  "One",\n  "Two",\n}\n', "One, Two"),
  ('author = [[\nFirst Line\nSecond Line\n]]\n', "First Line Second Line"),
  ('description = "no author"\n', None),
])
def test_parse_author(content, expected):
  assert dbmodule.parseAuthor(content) == expected

def test_build_loads_scripts_and_categories(db):
  assert names(db.searchAll()) == ["dns-txid.nse", "http-title.nse", "http-vuln.nse", "missing.nse"]
  assert names(db.searchByCriterial(category="safe")) == ["dns-txid.nse", "http-title.nse"]
  assert names(db.searchByCriterial(author="Calderon")) == ["http-vuln.nse"]
  assert names(db.searchByCriterial(name="http", category="vuln", author="Amar")) == ["http-vuln.nse"]

def test_category_ids_are_integers(db):
  conn = sqlite3.connect(db.dbname)
  types = conn.execute("select distinct typeof(id_category) from script_category").fetchall()
  conn.close()
  assert types == [("integer",)]

def test_search_ignores_sql_injection(db):
  db.createFavorite(name="secret", ranking="x")
  payload = "zz%'/**/UNION/**/SELECT/**/id,name,ranking/**/FROM/**/favorites--"
  assert db.searchByCriterial(name=payload) == {}
  assert db.searchByCriterial(name="o'brien") == {}
  assert db.getFavorites(name=payload) == {}

def test_favorites_lifecycle(db, capsys):
  db.createFavorite(name="a.nse")
  db.createFavorite(name="b.nse", ranking="great")
  assert names(db.getFavorites()) == ["a.nse", "b.nse"]
  assert names(db.getFavorites(name="b", ranking="great")) == ["b.nse"]
  db.updateFavorite(name="a.nse", newranking="ok")
  assert names(db.getFavorites(ranking="ok")) == ["a.nse"]
  db.updateFavorite(name="a.nse", newname="c.nse", newranking="top")
  assert names(db.getFavorites(ranking="top")) == ["c.nse"]
  db.deleteFavorite(name="c.nse")
  assert names(db.getFavorites()) == ["b.nse"]

def test_favorite_errors_do_not_raise(db, capsys):
  db.createFavorite(name="a.nse")
  db.createFavorite(name="a.nse")
  assert "[-] a.nse" in capsys.readouterr().out
  db.createFavorite(ranking="x")
  db.updateFavorite(newranking="x")
  db.updateFavorite(name="a.nse")
  db.updateFavorite(name="none", newranking="x")
  assert "[-] none" in capsys.readouterr().out
  db.deleteFavorite()
  db.deleteFavorite(name="none")
  assert "[-] none" in capsys.readouterr().out

def test_first_build_stores_sha256(db):
  assert len(checksum(db)) == 64

def test_unchanged_script_db_does_not_rebuild(db, monkeypatch):
  monkeypatch.setattr(db, "currentChecksum", checksum(db))
  def fail(cursor):
    raise AssertionError("rebuilt")
  monkeypatch.setattr(db, "setData", fail)
  db.updateApp()

def test_rebuild_keeps_favorites_and_updates_checksum(db, monkeypatch):
  db.createFavorite(name="keep.nse", ranking="great")
  with open(db.filePath, "a", encoding="utf-8") as f:
    f.write('Entry { filename = "new.nse", categories = { "safe", } }\n')
  old = checksum(db)
  monkeypatch.setattr(db, "currentChecksum", old)
  db.updateApp()
  assert "new.nse" in names(db.searchAll())
  assert names(db.getFavorites()) == ["keep.nse"]
  assert checksum(db) != old

def test_failed_rebuild_keeps_previous_data(db, monkeypatch, capsys):
  old = checksum(db)
  monkeypatch.setattr(db, "currentChecksum", "different")
  def fail(cursor, script, author):
    raise sqlite3.Error("boom")
  monkeypatch.setattr(db, "insertScript", fail)
  db.updateApp()
  assert "boom" in capsys.readouterr().out
  assert len(db.searchAll()) == 4
  assert checksum(db) == old

def test_favorite_messages_are_sanitized(db, capsys):
  name = "evil\x1b[2J"
  db.createFavorite(name=name)
  db.createFavorite(name=name)
  db.updateFavorite(name=name, newranking="ok")
  db.updateFavorite(name="none\x1b[2J", newranking="ok")
  db.deleteFavorite(name=name)
  db.deleteFavorite(name="none\x1b[2J")
  assert "\x1b" not in capsys.readouterr().out

STAGES = [{"name": "discovery", "arguments": "-sn"}, {"name": "ports", "arguments": "-F"}]

def workflowRun(db):
  runId = db.createRun("web", "10.0.0.0/24", STAGES)
  db.saveStageResults(runId, "discovery", [
    {"address": "10.0.0.1", "hostname": "one", "state": "up"},
    {"address": "10.0.0.2", "hostname": "", "state": "down"}], [], [])
  db.saveStageResults(runId, "ports", [], [
    {"address": "10.0.0.1", "protocol": "tcp", "port": 80, "state": "open", "service": "http", "product": "", "version": ""},
    {"address": "10.0.0.1", "protocol": "tcp", "port": 22, "state": "open", "service": "ssh", "product": "", "version": ""},
    {"address": "10.0.0.1", "protocol": "tcp", "port": 23, "state": "closed", "service": "telnet", "product": "", "version": ""}],
    [{"address": "10.0.0.1", "port": 80, "script": "http-title", "output": "Home"}])
  return runId

def test_workflow_results_are_queryable(db):
  runId = workflowRun(db)
  assert db.getLiveHosts(runId) == ["10.0.0.1"]
  assert db.getOpenPorts(runId) == {"10.0.0.1": [22, 80]}
  assert db.getOpenPorts(runId, ["http", "https"]) == {"10.0.0.1": [80]}
  details = db.getRun(runId)
  assert details["run"]["status"] == "running"
  assert [stage["name"] for stage in details["stages"]] == ["discovery", "ports"]
  assert details["findings"][0]["output"] == "Home"

def test_later_stage_keeps_known_service_details(db):
  runId = workflowRun(db)
  db.saveStageResults(runId, "services", [], [{"address": "10.0.0.1", "protocol": "tcp", "port": 80,
    "state": "open", "service": "", "product": "nginx", "version": "1.2"}], [])
  service = [item for item in db.getRun(runId)["services"] if item["port"] == 80][0]
  assert (service["service"], service["product"], service["version"]) == ("http", "nginx", "1.2")

def test_status_updates_and_missing_run(db):
  runId = workflowRun(db)
  db.setStageStatus(runId, 0, "completed")
  db.setRunStatus(runId, "completed")
  details = db.getRun(runId)
  assert details["stages"][0]["status"] == "completed"
  assert details["run"]["status"] == "completed" and details["run"]["finished_at"]
  assert db.getRuns()[0]["id"] == runId
  assert db.getRun(9999) is None

def test_rebuild_keeps_workflows(db, monkeypatch):
  runId = workflowRun(db)
  monkeypatch.setattr(db, "currentChecksum", "different")
  db.updateApp()
  assert db.getLiveHosts(runId) == ["10.0.0.1"]

def test_workflow_tables_are_added_to_existing_databases(db):
  conn = sqlite3.connect(db.dbname)
  tables = [row[0] for row in conn.execute("select name from sqlite_master where name like 'workflow%'")]
  conn.close()
  assert tables == []
  assert db.getRuns() == []

def test_script_categories(db):
  categories = db.scriptCategories()
  assert categories["http-title"] == {"default", "safe"}
  assert "http-title.nse" not in categories
