import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_bash_check_runs_before_bash_only_syntax():
  with open(os.path.join(ROOT, "install.sh"), encoding="utf-8") as f:
    script = f.read()
  check = script.index('if [ -z "${BASH_VERSION:-}" ]; then')
  assert check < script.index("set -euo pipefail")
  assert check < script.index("function ")
  assert "bash install.sh" in script[check:script.index("set -euo pipefail")]
