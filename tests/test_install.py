import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_bash_check_runs_before_bash_only_syntax():
  with open(os.path.join(ROOT, "install.sh"), encoding="utf-8") as f:
    script = f.read()
  check = script.index('if [ -z "${BASH_VERSION:-}" ]; then')
  assert check < script.index("set -euo pipefail")
  assert check < script.index("function ")
  assert "bash install.sh" in script[check:script.index("set -euo pipefail")]

def script():
  with open(os.path.join(ROOT, "install.sh"), encoding="utf-8") as f:
    return f.read()

def requirePython(tmp_path, code):
  python = tmp_path / "python3"
  python.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then echo "Python 3.11.9"; exit 0; fi\nexit ' + str(code) + "\n", encoding="utf-8")
  python.chmod(0o755)
  function = re.search(r"function requirePython\(\)\{.*?\n\}", script(), re.DOTALL).group(0)
  return subprocess.run(["bash", "-c", function + "\nrequirePython\necho reached"], capture_output=True, text=True, check=False,
    env={"PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]}, stdin=subprocess.DEVNULL)

def test_installer_stops_on_an_old_python(tmp_path):
  result = requirePython(tmp_path, 1)
  assert result.returncode == 1
  assert "reached" not in result.stdout
  assert "Python 3.12 or later" in result.stderr and "Python 3.11.9" in result.stderr

def test_installer_accepts_a_supported_python(tmp_path):
  result = requirePython(tmp_path, 0)
  assert result.returncode == 0 and "reached" in result.stdout

def test_installer_checks_python_for_3_12_before_creating_the_environment():
  text = script()
  assert "sys.version_info < (3, 12)" in text
  assert text.rindex("requirePython\n") < text.rindex("installRequirements\n")

@pytest.mark.parametrize("version,stops", [((3, 11, 9), True), ((3, 12, 0), False)])
def test_nsearch_checks_python_before_importing_anything_else(version, stops):
  code = ("import runpy, sys\n"
    "sys.version_info = " + repr(version) + "\n"
    "try:\n"
    "  runpy.run_path('nsearch.py', run_name='not_main')\n"
    "finally:\n"
    "  print('console' in sys.modules)\n")
  result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL)
  if stops:
    assert result.returncode == 1
    assert "Python 3.12 or later" in result.stderr
    assert result.stdout.strip() == "False"
  else:
    assert result.returncode == 0 and result.stdout.strip().endswith("True")
