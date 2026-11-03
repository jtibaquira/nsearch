import pytest

import dbmodule
import helper

@pytest.mark.parametrize("args,expected", [
  ("", {}),
  ("name:http", {"name": "http"}),
  ("name:http category:vuln", {"name": "http", "category": "vuln"}),
  ('author:"Paulino Calderon"', {"author": "Paulino Calderon"}),
  ("foo:bar", None),
  ("name", None),
  ("name:", None),
  ("name:a name:b", None),
  ('name:"unclosed', None),
])
def test_parse_args(args, expected):
  assert helper.parseArgs(args, ("name", "category", "author")) == expected

def test_parse_args_keeps_colons_in_value():
  assert helper.parseArgs("net:fe80::1", ("net",)) == {"net": "fe80::1"}

def test_sanitize_removes_control_characters():
  assert helper.sanitize("a\x1b[31mb\tc\x9b") == "a?[31mb\tc?"

@pytest.mark.parametrize("command,args", [
  ("search", "foo:bar"),
  ("search", "name"),
  ("addfav", "foo"),
  ("addfav", "ranking:x"),
  ("addfav", ""),
  ("modfav", "ranking:x"),
  ("modfav", "name:x"),
  ("delfav", "foo"),
  ("delfav", ""),
  ("showfav", "foo:bar"),
  ("unknown", ""),
])
def test_invalid_input_does_not_raise(db, command, args):
  helper.Helper(args, command).process()

def test_last_remembers_result_type(db, capsys):
  db.createFavorite(name="a.nse", ranking="great")
  helper.Helper("", "showfav").process()
  capsys.readouterr()
  helper.Helper().printlastResult()
  assert "Ranking" in capsys.readouterr().out
  helper.Helper("name:http", "search").process()
  capsys.readouterr()
  helper.Helper().printlastResult()
  out = capsys.readouterr().out
  assert "Author" in out and "http-title.nse" in out

def test_results_are_sanitized(db, capsys):
  db.createFavorite(name="\x1b[31mevil", ranking="\x1b[32mx")
  capsys.readouterr()
  helper.Helper("", "showfav").process()
  assert "\x1b[31m" not in capsys.readouterr().out

def test_resultitems(db):
  helper.Helper("name:http", "search").process()
  assert sorted(helper.Helper().resultitems()) == ["http-title.nse", "http-vuln.nse"]

@pytest.mark.parametrize("name", ["../../../etc/passwd", "/etc/passwd", "..", ".hidden", "a/b", "a\\b", "nope"])
def test_doc_rejects_invalid_names(db, capsys, name):
  helper.Helper(name).displayDoc()
  assert "Script not found" in capsys.readouterr().out

@pytest.mark.parametrize("name", ["http-title", "http-title.nse"])
def test_doc_shows_script(db, capsys, name):
  helper.Helper(name).displayDoc()
  out = capsys.readouterr().out
  assert "localhost" in out
  assert "shortport" not in out
