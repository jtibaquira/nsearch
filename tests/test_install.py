import os
import re
import shutil
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

UNIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="install.sh is the Unix installer; Windows uses install.ps1, tested below and in CI")

def requirePython(tmp_path, code):
  python = tmp_path / "python3"
  python.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then echo "Python 3.11.9"; exit 0; fi\nexit ' + str(code) + "\n", encoding="utf-8")
  python.chmod(0o755)
  function = re.search(r"function requirePython\(\)\{.*?\n}", script(), re.DOTALL).group(0)
  return subprocess.run(["bash", "-c", function + "\nrequirePython\necho reached"], capture_output=True, text=True, check=False,
    env={"PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]}, stdin=subprocess.DEVNULL)

@UNIX_ONLY
def test_installer_stops_on_an_old_python(tmp_path):
  result = requirePython(tmp_path, 1)
  assert result.returncode == 1
  assert "reached" not in result.stdout
  assert "Python 3.12 or later" in result.stderr and "Python 3.11.9" in result.stderr

@UNIX_ONLY
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

@UNIX_ONLY
def test_installer_explains_a_missing_python(tmp_path):
  function = re.search(r"function requirePython\(\)\{.*?\n}", script(), re.DOTALL).group(0)
  bash = shutil.which("bash")
  result = subprocess.run([bash, "-c", function + "\nrequirePython\necho reached"], capture_output=True, text=True, check=False,
    env={"PATH": str(tmp_path)}, stdin=subprocess.DEVNULL)
  assert result.returncode == 1 and "reached" not in result.stdout
  assert "python3 is not installed" in result.stderr and "command not found" not in result.stderr


def powershell():
  with open(os.path.join(ROOT, "install.ps1"), encoding="utf-8") as f:
    return f.read()

def test_install_ps1_declares_nmapdir_parameter():
  text = powershell()
  assert 'param([string]$NmapDir' in text

def test_install_ps1_has_strict_mode_and_error_action():
  text = powershell()
  assert "Set-StrictMode -Version Latest" in text
  assert "$ErrorActionPreference = 'Stop'" in text

def test_install_ps1_checks_python_3_12():
  text = powershell()
  assert "sys.version_info < (3, 12)" in text

def test_install_ps1_has_required_sids():
  text = powershell()
  assert "S-1-5-18" in text
  assert "S-1-5-32-544" in text

def test_install_ps1_has_inheritance_r_flag():
  text = powershell()
  assert "/inheritance:r" in text

def test_install_ps1_has_oi_ci_f_flags():
  text = powershell()
  assert "(OI)(CI)F" in text

def test_install_ps1_does_not_change_execution_policy_or_install_winget():
  text = powershell()
  assert "Set-ExecutionPolicy" not in text
  assert "winget install" not in text

def test_install_ps1_sets_permissions_before_venv():
  text = powershell()
  lastFunctionEnd = text.rindex("\n}\n")
  venvInvocation = text.index('"-m" "venv"')
  assert venvInvocation > lastFunctionEnd

def test_install_ps1_creates_config_with_required_keys():
  text = powershell()
  assert "scriptsPath:" in text
  assert "filePath:" in text
  assert "fileBackup:" in text
  assert "scriptdb:" in text
  assert "categories:" in text
  assert "checksum:" in text

def test_convert_to_yaml_quoted_implementation():
  text = powershell()
  functionStart = text.index("function ConvertTo-YamlQuoted")
  functionEnd = text.index("\n}", functionStart)
  functionBody = text[functionStart:functionEnd]
  # Check for .Replace("'","''") pattern - the simplified implementation
  assert "Replace" in functionBody and "'','''''" in functionBody or ".Replace(\"'\", \"''\")" in functionBody or "$text.Replace('\"', '\"'')'" in functionBody
  # Should NOT have backslash escaping
  assert r'\\"' not in functionBody

def test_config_yaml_no_double_quotes_in_convertcall():
  text = powershell()
  assert "''$(ConvertTo-YamlQuoted" not in text

def test_python_not_as_single_string_py_minus_3():
  text = powershell()
  assert '"py -3"' not in text

def test_install_ps1_does_not_use_exe_after_functions():
  """Verify that $exe is not used after RequirePython function definitions."""
  text = powershell()
  # Find where all functions end (last closing brace before main code)
  lastFunctionEnd = text.rindex("\n}\n")
  # After functions, there should be no usage of $exe variable
  mainCode = text[lastFunctionEnd:]
  # Should use $pythonExe instead of $exe in the main part
  assert "$pythonExe" in mainCode
  # Main code should not have & $exe pattern
  assert "& $exe " not in mainCode

def test_install_ps1_findnmap_called_with_requesteddir():
  """Verify that FindNmap is called with -requestedDir parameter."""
  text = powershell()
  # Check that the function has the renamed parameter
  assert 'param([string]$requestedDir' in text
  # Check that it's called with -requestedDir $NmapDir
  mainStart = text.rindex("\n}\n")
  mainCode = text[mainStart:]
  assert "FindNmap -requestedDir" in mainCode

def test_install_ps1_banner_no_backtick_escapes():
  """Verify that the banner does not use backtick escapes for quotes."""
  text = powershell()
  # Banner is between lines 9-14 approximately
  # Check for backtick patterns used for escaping like `| or `'
  assert r"`|" not in text
  assert r"`'" not in text

def test_install_ps1_looks_in_the_install_folders_before_path():
  text = powershell()
  findNmap = text[text.index("function FindNmap"):text.index("function ConvertTo-YamlQuoted")]
  assert findNmap.index("C:\\Program Files (x86)\\Nmap") < findNmap.index("Get-Command nmap.exe")

def test_install_ps1_banner_matches_the_console_banner():
  text = powershell()
  assert "\\`" not in text
  assert "Write-Host '| . ` | `--. \\|  __|  / _` || ''__| / __|| ''_  |'" in text

def test_install_ps1_reads_the_permissions_as_sids():
  text = powershell()
  assert "GetAccessRules($true, $true, $sidType)" in text
  assert ".SecurityIdentifier.Value" not in text

def test_install_ps1_removes_other_accounts_before_resetting_the_files():
  text = powershell()
  permissions = text[text.index("function SetFolderPermissions"):text.index('Write-Host "[+] Checking dependencies')]
  assert "/remove:g" in permissions
  assert "$allowed -notcontains" in permissions
  assert permissions.index("/remove:g") < permissions.index("/reset /T")
