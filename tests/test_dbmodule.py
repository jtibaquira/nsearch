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
