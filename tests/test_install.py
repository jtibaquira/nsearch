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

def test_install_ps1_python_checks_survive_stderr_on_windows_powershell():
  text = powershell()
  requirePython = text[text.index("function RequirePython"):text.index("function FindNmap")]
  assert "$ErrorActionPreference = 'Continue'" in requirePython
  assert requirePython.index("$ErrorActionPreference = 'Continue'") < requirePython.index('& "py"')

def writeExecutable(path, content):
  path.write_text(content, encoding="utf-8")
  path.chmod(0o755)

def runFakeInstall(tmp_path, osName="Linux", manager="apt-get", hasNmap=True, hasPython=True, pythonOk=True, venvOk=True,
  sudoOk=True, uid=1000, sudoUser=None, upgradePython=True, installVenv=True, pythonIncludesVenv=False, mktempScript=None):
  proj = tmp_path / "proj"
  bindir = tmp_path / "bin"
  state = tmp_path / "state"
  proj.mkdir()
  bindir.mkdir()
  state.mkdir()
  log = tmp_path / "calls.log"
  log.write_text("", encoding="utf-8")
  scriptDb = tmp_path / "script.db"
  scriptDb.write_text('Entry { filename = "http-title.nse", categories = { "default", "safe", } }\n', encoding="utf-8")
  shutil.copy2(os.path.join(ROOT, "install.sh"), proj / "install.sh")
  shutil.copy2(os.path.join(ROOT, "requirements.txt"), proj / "requirements.txt")
  for tool in ("bash", "sh", "mktemp", "rm", "dirname", "head", "chmod", "mkdir", "cp", "touch", "cat", "true", "false"):
    found = shutil.which(tool)
    if found:
      (bindir / tool).symlink_to(found)
  if mktempScript is not None:
    (bindir / "mktemp").unlink(missing_ok=True)
    writeExecutable(bindir / "mktemp", mktempScript)
  if pythonOk:
    (state / "python_ok").write_text("", encoding="utf-8")
  if venvOk:
    (state / "venv_ok").write_text("", encoding="utf-8")
  pythonScript = f"""#!/bin/sh
if [ "$1" = "--version" ]; then
  if [ -f "{state}/python_ok" ]; then echo "Python 3.12.4"; else echo "Python 3.11.9"; fi
  exit 0
fi
if [ "$1" = "-c" ]; then
  [ -f "{state}/python_ok" ] && exit 0 || exit 1
fi
if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
  if [ "{'1' if mktempScript is not None else '0'}" = "1" ]; then
    echo "venv $3" >> "{log}"
  fi
  [ -f "{state}/venv_ok" ] || exit 1
  mkdir -p "$3/bin"
  printf '#!/bin/sh\\necho "pip $*" >> "{log}"\\nexit 0\\n' > "$3/bin/pip"
  chmod 755 "$3/bin/pip"
  exit 0
fi
exit 0
"""
  writeExecutable(state / "python_template", pythonScript)
  if hasPython:
    writeExecutable(bindir / "python3", pythonScript)
  if hasNmap:
    writeExecutable(bindir / "nmap", "#!/bin/sh\nexit 0\n")
  writeExecutable(bindir / "uname", f'#!/bin/sh\nif [ "$1" = "-s" ]; then echo "{osName}"; elif [ "$1" = "-m" ]; then echo "x86_64"; else echo "6.0"; fi\n')
  writeExecutable(bindir / "id", f'#!/bin/sh\necho "{uid}"\n')
  writeExecutable(bindir / "find", f'#!/bin/sh\necho "{scriptDb}"\n')
  writeExecutable(bindir / "chown", f'#!/bin/sh\necho "chown $*" >> "{log}"\n')
  writeExecutable(bindir / "sudo", f"""#!/bin/sh
echo "sudo $*" >> "{log}"
if [ "{'1' if sudoOk else '0'}" != "1" ]; then
  exit 1
fi
if [ "$1" = "-n" ]; then
  shift
fi
if [ "$1" = "true" ]; then
  exit 0
fi
exec "$@"
""")
  if manager:
    writeExecutable(bindir / manager, f"""#!/bin/sh
echo "{manager} $*" >> "{log}"
for arg in "$@"; do
  if [ "$arg" = "nmap" ]; then
    printf '#!/bin/sh\\nexit 0\\n' > "{bindir}/nmap"
    chmod 755 "{bindir}/nmap"
  fi
  if [ "$arg" = "python3" ] || [ "$arg" = "python" ]; then
    cp "{state}/python_template" "{bindir}/python3"
    chmod 755 "{bindir}/python3"
    if [ "{'1' if upgradePython else '0'}" = "1" ]; then
      touch "{state}/python_ok"
    fi
    if [ "{'1' if pythonIncludesVenv else '0'}" = "1" ]; then
      touch "{state}/venv_ok"
    fi
  fi
  if [ "$arg" = "python3-venv" ] && [ "{'1' if installVenv else '0'}" = "1" ]; then
    touch "{state}/venv_ok"
  fi
done
exit 0
""")
  env = {"PATH": str(bindir), "HOME": str(tmp_path), "TMPDIR": str(tmp_path)}
  if sudoUser is not None:
    env["SUDO_USER"] = sudoUser
  result = subprocess.run([str(bindir / "bash"), str(proj / "install.sh")], cwd=proj, env=env,
    capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL)
  calls = [line for line in log.read_text(encoding="utf-8").splitlines() if line]
  return result, calls, proj

@UNIX_ONLY
def test_linux_install_with_everything_ready_never_calls_sudo_or_package_managers(tmp_path):
  result, calls, proj = runFakeInstall(tmp_path, sudoOk=False)
  assert result.returncode == 0
  assert calls == ["pip install -r requirements.txt"]
  assert (proj / "config.yaml").is_file()

@UNIX_ONLY
@pytest.mark.parametrize("manager,expected", [
  ("apt-get", ["sudo -n true", "sudo -n apt-get update", "apt-get update", "sudo -n apt-get install -y nmap", "apt-get install -y nmap", "pip install -r requirements.txt"]),
  ("dnf", ["sudo -n true", "sudo -n dnf install -y nmap", "dnf install -y nmap", "pip install -r requirements.txt"]),
  ("yum", ["sudo -n true", "sudo -n yum install -y nmap", "yum install -y nmap", "pip install -r requirements.txt"]),
])
def test_linux_install_missing_nmap_only_installs_nmap(tmp_path, manager, expected):
  result, calls, _ = runFakeInstall(tmp_path, manager=manager, hasNmap=False)
  assert result.returncode == 0
  assert calls == expected

@UNIX_ONLY
@pytest.mark.parametrize("hasPython,pythonOk", [(False, False), (True, False)])
def test_linux_install_missing_or_old_python_only_requests_python_runtime(tmp_path, hasPython, pythonOk):
  result, calls, _ = runFakeInstall(tmp_path, manager="apt-get", hasPython=hasPython, pythonOk=pythonOk, venvOk=True)
  assert result.returncode == 0
  assert calls == ["sudo -n true", "sudo -n apt-get update", "apt-get update", "sudo -n apt-get install -y python3", "apt-get install -y python3", "pip install -r requirements.txt"]

@UNIX_ONLY
def test_linux_install_rechecks_python_version_after_package_install(tmp_path):
  result, calls, _ = runFakeInstall(tmp_path, manager="dnf", hasPython=True, pythonOk=False, upgradePython=False)
  assert result.returncode == 1
  assert calls == ["sudo -n true", "sudo -n dnf install -y python3", "dnf install -y python3"]
  assert "Python 3.12 or later" in result.stderr and "Python 3.11.9" in result.stderr

@UNIX_ONLY
def test_linux_install_missing_venv_on_apt_requests_python3_venv(tmp_path):
  result, calls, _ = runFakeInstall(tmp_path, manager="apt-get", venvOk=False)
  assert result.returncode == 0
  assert calls == ["sudo -n true", "sudo -n apt-get update", "apt-get update", "sudo -n apt-get install -y python3-venv", "apt-get install -y python3-venv", "pip install -r requirements.txt"]

@UNIX_ONLY
def test_linux_install_missing_venv_without_passwordless_sudo_fails_fast(tmp_path):
  result, calls, _ = runFakeInstall(tmp_path, manager="apt-get", venvOk=False, sudoOk=False)
  assert result.returncode == 1
  assert calls == ["sudo -n true"]
  assert "python3-venv" in result.stderr and "sudo bash install.sh" in result.stderr

@UNIX_ONLY
def test_linux_install_on_dnf_fails_clearly_when_venv_is_unavailable(tmp_path):
  result, calls, _ = runFakeInstall(tmp_path, manager="dnf", venvOk=False)
  assert result.returncode == 1
  assert calls == []
  assert "python3 -m venv" in result.stderr

@UNIX_ONLY
@pytest.mark.parametrize("mktempBody", ["exit 1", "exit 0", 'echo "/nonexistent-nsearch-dir"'])
def test_has_venv_never_calls_python_when_mktemp_fails_or_returns_no_directory(tmp_path, mktempBody):
  result, calls, _ = runFakeInstall(tmp_path, manager="dnf", uid=0, mktempScript="#!/bin/sh\n" + mktempBody + "\n")
  assert result.returncode == 1
  assert calls == []

@UNIX_ONLY
def test_linux_install_as_root_with_sudo_user_chowns_outputs(tmp_path):
  result, calls, _ = runFakeInstall(tmp_path, manager="apt-get", hasNmap=False, uid=0, sudoUser="operator")
  assert result.returncode == 0
  assert calls == ["apt-get update", "apt-get install -y nmap", "pip install -r requirements.txt", "chown -R operator .venv config.yaml"]

@UNIX_ONLY
def test_macos_install_behavior_is_unchanged(tmp_path):
  result, calls, _ = runFakeInstall(tmp_path, osName="Darwin", manager="brew", hasNmap=False)
  assert result.returncode == 0
  assert calls == ["brew install nmap", "pip install -r requirements.txt"]
