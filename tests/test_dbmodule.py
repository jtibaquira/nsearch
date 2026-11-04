import json
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
  service = next(item for item in db.getRun(runId)["services"] if item["port"] == 80)
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

def test_a_database_error_in_search_is_reported(db, capsys):
  connection = db.lite.connect(db.dbname)
  connection.execute("DROP TABLE script_category")
  connection.execute("DROP TABLE scripts")
  connection.commit()
  connection.close()
  assert db.searchAll() is None
  assert capsys.readouterr().out == "Error no such table: scripts:\n"

def test_an_unexpected_error_in_search_reaches_the_console(db, monkeypatch, capsys):
  import console
  def fail(*args):
    raise ValueError("boom")
  monkeypatch.setattr(db, "__fetchScript", fail)
  assert not console.Console().onecmd("search")
  assert capsys.readouterr().out == "Error: boom\n"

# ---- Observations of a workflow run

def test_a_later_state_keeps_the_evidence_that_the_port_was_open(db):
  runId = db.createRun("w", "10.0.0.1", [{"name": "ports", "arguments": "-F"}])
  service = {"address": "10.0.0.1", "protocol": "tcp", "port": 22, "state": "open", "service": "ssh", "product": "", "version": ""}
  db.saveStageResults(runId, "ports", [], [service], [])
  db.saveStageResults(runId, "services", [], [dict(service, state="filtered")], [])
  assert db.getOpenPorts(runId) == {}
  assert db.getOpenServices(runId) == set()
  assert db.getSeenPorts(runId) == {("10.0.0.1", "tcp", 22)}

def test_a_missing_observation_is_not_used_as_a_target(db):
  runId = db.createRun("w", "10.0.0.1", [{"name": "ports", "arguments": "-F"}])
  service = {"address": "10.0.0.1", "protocol": "tcp", "port": 22, "state": "open", "service": "ssh", "product": "", "version": ""}
  db.saveStageResults(runId, "ports", [{"address": "10.0.0.1", "hostname": "", "state": "up"}], [service], [])
  db.recordObservations(runId, 0, [{"type": "host_missing", "address": "10.0.0.1"}], ["10.0.0.1"], [("10.0.0.1", "tcp", 22)])
  details = db.getRun(runId)
  assert db.getOpenPorts(runId) == {}
  assert db.getLiveHosts(runId) == []
  assert details["services"] == []
  assert details["hosts"][0]["state"] == "up"
  assert db.getSeenPorts(runId) == {("10.0.0.1", "tcp", 22)}
  db.saveStageResults(runId, "ports", [{"address": "10.0.0.1", "hostname": "", "state": "up"}], [service], [])
  assert db.getOpenPorts(runId) == {"10.0.0.1": [22]}
  assert db.getLiveHosts(runId) == ["10.0.0.1"]

def test_repeated_warnings_are_saved_once(db):
  runId = db.createRun("w", "10.0.0.1", [{"name": "ports", "arguments": "-F"}])
  warning = {"type": "host_missing", "address": "10.0.0.1"}
  db.recordObservations(runId, 0, [warning])
  db.recordObservations(runId, 0, [warning])
  assert json.loads(db.getRun(runId)["stages"][0]["warnings"]) == [warning]

def test_earlier_runs_only_lists_older_runs_of_the_target_with_the_status(db):
  first = db.createRun("w", "10.0.0.1", [])
  db.setRunStatus(first, "completed")
  failed = db.createRun("w", "10.0.0.1", [])
  db.setRunStatus(failed, "failed")
  other = db.createRun("w", "10.0.0.2", [])
  db.setRunStatus(other, "completed")
  second = db.createRun("w", "10.0.0.1", [])
  db.setRunStatus(second, "completed")
  last = db.createRun("w", "10.0.0.1", [])
  assert db.getEarlierRuns(last, "10.0.0.1", ("completed",)) == [second, first]
  assert db.getEarlierRuns(first, "10.0.0.1", ("completed",)) == []

def test_a_database_from_an_earlier_version_keeps_its_results(db):
  conn = sqlite3.connect(db.dbname)
  conn.executescript("""
    create table workflow_runs(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, workflow TEXT NOT NULL, target TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT NULL);
    create table workflow_stages(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, run_id INTEGER NOT NULL, position INTEGER NOT NULL, name TEXT NOT NULL, arguments TEXT NOT NULL, status TEXT NOT NULL, definition TEXT NULL, targets TEXT NULL, UNIQUE(run_id, position));
    create table workflow_hosts(run_id INTEGER NOT NULL, address TEXT NOT NULL, hostname TEXT NULL, state TEXT NOT NULL, PRIMARY KEY(run_id, address));
    create table workflow_services(run_id INTEGER NOT NULL, address TEXT NOT NULL, protocol TEXT NOT NULL, port INTEGER NOT NULL, state TEXT NOT NULL, service TEXT NULL, product TEXT NULL, version TEXT NULL, PRIMARY KEY(run_id, address, protocol, port));
    insert into workflow_runs values (1, 'w', '10.0.0.1', 'completed', 'x', 'y');
    insert into workflow_stages values (1, 1, 0, 'ports', '-F', 'completed', NULL, NULL);
    insert into workflow_hosts values (1, '10.0.0.1', 'h', 'up');
    insert into workflow_services values (1, '10.0.0.1', 'tcp', 22, 'open', 'ssh', '', '');
    insert into workflow_services values (1, '10.0.0.1', 'tcp', 23, 'filtered', 'telnet', '', '');
  """)
  conn.commit()
  conn.close()
  details = db.getRun(1)
  assert details["stages"][0]["warnings"] is None
  assert [item["port"] for item in details["services"]] == [22]
  assert details["services"][0]["ever_open"] is None
  assert db.getOpenPorts(1) == {"10.0.0.1": [22]}
  assert db.getLiveHosts(1) == ["10.0.0.1"]
  # A port that is filtered now may have been open before this was recorded, and nothing claims it was
  assert db.getSeenPorts(1) == {("10.0.0.1", "tcp", 22)}

def test_a_port_first_seen_filtered_and_then_open_counts_as_seen(db):
  runId = db.createRun("w", "10.0.0.1", [{"name": "ports", "arguments": "-F"}])
  service = {"address": "10.0.0.1", "protocol": "tcp", "port": 22, "state": "filtered", "service": "ssh", "product": "", "version": ""}
  db.saveStageResults(runId, "ports", [], [service], [])
  assert db.getSeenPorts(runId) == set()
  db.saveStageResults(runId, "services", [], [dict(service, state="open")], [])
  db.saveStageResults(runId, "scripts", [], [service], [])
  assert db.getSeenPorts(runId) == {("10.0.0.1", "tcp", 22)}
