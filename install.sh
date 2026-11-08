#!/usr/bin/env bash

# This check must stay POSIX: sh stops at the first bash-only line below
if [ -z "${BASH_VERSION:-}" ]; then
  echo "[-] This script requires bash. Run it with: bash install.sh" >&2
  exit 1
fi

set -euo pipefail

printf "\n"
echo "=================================================";
echo " _   _  _____  _____                     _     ";
echo "| \ | |/  ___||  ___|                   | |    ";
echo "|  \| |\ \`--. | |__    __ _  _ __   ___ | |__  ";
echo "| . \` | \`--. \|  __|  / _\` || '__| / __|| '_ \ ";
echo "| |\  |/\__/ /| |___ | (_| || |   | (__ | | | |";
echo "\_| \_/\____/ \____/  \__,_||_|    \___||_| |_|";
echo "=================================================";
echo " Version 0.5b  https://github.com/jtibaquira/nsearch  @jjtibaquira";
echo " Email: jacobotibaquira@gmail.com";
echo "=================================================";
printf "\n"

cd "$(dirname "$0")"

os="$(uname -s) $(uname -r)"
arch=$(uname -m)

SUDO=""

function hasPython312(){
  command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' >/dev/null 2>&1
}

function hasVenv(){
  command -v python3 >/dev/null 2>&1 || return 1
  local tmp status=0
  tmp=$(mktemp -d 2>/dev/null) || return 1
  if [ -z "$tmp" ] || [ ! -d "$tmp" ]; then
    return 1
  fi
  python3 -m venv "$tmp/venv" >/dev/null 2>&1 || status=$?
  rm -rf "$tmp"
  return "$status"
}

function requireVenv(){
  if ! hasVenv; then
    echo "[-] python3 cannot create a virtual environment (python3 -m venv failed). Install the venv package for your distribution (such as python3-venv), then run this script again." >&2
    exit 1
  fi
}

function ensurePrivileges(){
  if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
    return
  fi
  if ! command -v sudo >/dev/null 2>&1 || ! sudo -n true >/dev/null 2>&1; then
    echo "[-] Missing system packages ($*) and passwordless sudo is not available. Install them manually or run: sudo bash install.sh" >&2
    exit 1
  fi
  SUDO="sudo -n"
}

function installLinuxPackages(){
  local manager=""
  if command -v apt-get >/dev/null 2>&1; then
    manager="apt-get"
  elif command -v dnf >/dev/null 2>&1; then
    manager="dnf"
  elif command -v yum >/dev/null 2>&1; then
    manager="yum"
  fi

  local packages=()
  local venvOk=0
  if ! command -v nmap >/dev/null 2>&1; then
    packages+=(nmap)
  fi
  if ! hasPython312; then
    packages+=(python3)
  elif hasVenv; then
    venvOk=1
  elif [ "$manager" = "apt-get" ]; then
    packages+=(python3-venv)
  fi

  if [ "${#packages[@]}" -eq 0 ] && [ "$venvOk" -eq 1 ]; then
    return
  fi

  if [ -z "$manager" ]; then
    requireTools
    requirePython
    requireVenv
    return
  fi

  local needUpdate=0
  if [ "${#packages[@]}" -gt 0 ]; then
    ensurePrivileges "${packages[@]}"
    if [ "$manager" = "apt-get" ]; then
      $SUDO apt-get update
      needUpdate=1
      $SUDO apt-get install -y "${packages[@]}"
    else
      $SUDO "$manager" install -y "${packages[@]}"
    fi
  fi

  requireTools
  requirePython
  if [ "$venvOk" -eq 0 ] && ! hasVenv; then
    if [ "$manager" = "apt-get" ] && [[ " ${packages[*]} " != *" python3-venv "* ]]; then
      ensurePrivileges python3-venv
      if [ "$needUpdate" -eq 0 ]; then
        $SUDO apt-get update
      fi
      $SUDO apt-get install -y python3-venv
    fi
    requireVenv
  fi
}

function installMacPackages(){
  if ! command -v brew >/dev/null 2>&1; then
    requireTools
    return
  fi
  command -v nmap >/dev/null 2>&1 || brew install nmap
  command -v python3 >/dev/null 2>&1 || brew install python
}

function requireTools(){
  if ! command -v nmap >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
    echo "[-] No automatic install available for $os ($arch). Install nmap and python3, then run this script again." >&2
    exit 1
  fi
}

function requirePython(){
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[-] NSEarch requires Python 3.12 or later, and python3 is not installed. Install it, then run this script again." >&2
    exit 1
  fi
  if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
    echo "[-] NSEarch requires Python 3.12 or later, and python3 is $(python3 --version). Install a newer Python, then run this script again." >&2
    exit 1
  fi
}

function installRequirements(){
  printf "[+] Installing Python requirements in .venv ...\n"
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
}

function findScriptDb(){
  local dir
  for dir in /usr/share/nmap/scripts /usr/local/share/nmap/scripts /opt/homebrew/share/nmap/scripts; do
    if [ -f "$dir/script.db" ]; then
      echo "$dir/script.db"
      return
    fi
  done
  find /usr /opt -type f -name script.db 2>/dev/null | head -n 1
}

function createConfigFile(){
  local filePath scriptsPath
  filePath=$(findScriptDb)
  if [ -z "$filePath" ]; then
    echo "[-] Could not find nmap's script.db, so config.yaml was not created." >&2
    exit 1
  fi
  scriptsPath="$(dirname "$filePath")/"
  printf "[+] Creating config.yaml file ...\n"
  (
    umask 077
    {
      printf "config:\n"
      printf "  scriptsPath: '%s'\n" "$scriptsPath"
      printf "  filePath: '%s'\n" "$filePath"
      printf "  fileBackup: 'scriptbk.db'\n"
      printf "  scriptdb: 'nmap_scripts.sqlite3'\n"
      printf '  categories: ["auth","broadcast","brute","default","discovery","dos","exploit","external","fuzzer","intrusive","malware","safe","version","vuln"]\n'
      printf "  checksum: ''\n"
    } > config.yaml
  )
  chmod 600 config.yaml
}

printf "[+] Checking dependencies for %s (%s) ...\n" "$os" "$arch"
case "$(uname -s)" in
  Darwin) installMacPackages ;;
  Linux) installLinuxPackages ;;
  *) requireTools ;;
esac

requirePython
installRequirements
createConfigFile

if [ -n "${SUDO_USER:-}" ]; then
  chown -R "$SUDO_USER" .venv config.yaml
fi

printf "[+] NSEarch is ready. Run it with: .venv/bin/python nsearch.py\n"
