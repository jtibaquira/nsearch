param([string]$NmapDir = "")
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location -LiteralPath $PSScriptRoot

Write-Host ""
Write-Host '================================================='
Write-Host ' _   _  _____  _____                     _'
Write-Host '| \ | |/  ___||  ___|                   | |'
Write-Host '|  \| |\ `--. | |__    __ _  _ __   ___ | |__'
Write-Host '| . ` | `--. \|  __|  / _` || ''__| / __|| ''_  |'
Write-Host '| |\  |/\__/ /| |___ | (_| || |   | (__ | | | |'
Write-Host '\_| \_/\____/ \____/  \__,_||_|    \___||_| |_|'
Write-Host '================================================='
Write-Host " Version 0.5b  https://github.com/jtibaquira/nsearch  @jjtibaquira"
Write-Host " Email: jacobotibaquira@gmail.com"
Write-Host '================================================='
Write-Host ""

function RequirePython {
  # Windows PowerShell 5.1 turns what py or python print on stderr into an error, and 'Stop' would end the script here instead of reaching the messages below
  $ErrorActionPreference = 'Continue'
  $exe = ""
  $pyArgs = @()
  if (Get-Command "py" -ErrorAction SilentlyContinue) {
    $null = & "py" @("-3") "--version" 2>&1
    if ($LASTEXITCODE -eq 0) {
      $exe = "py"
      $pyArgs = @("-3")
    }
  }
  if (-not $exe -and (Get-Command "python" -ErrorAction SilentlyContinue)) {
    $null = & "python" "--version" 2>&1
    if ($LASTEXITCODE -eq 0) {
      $exe = "python"
      $pyArgs = @()
    }
  }
  if (-not $exe) {
    Write-Host "[-] NSEarch requires Python 3.12 or later, but Python is not installed. Install it, then run this script again." -ForegroundColor Red
    Write-Host "    You can search for Python with: winget search Python.Python"
    exit 1
  }
  $null = & $exe @pyArgs "-c" "import sys; sys.exit(sys.version_info < (3, 12))"
  if ($LASTEXITCODE -ne 0) {
    $version = & $exe @pyArgs "--version" 2>&1
    Write-Host "[-] NSEarch requires Python 3.12 or later, and $version is installed. Install a newer Python, then run this script again." -ForegroundColor Red
    exit 1
  }
  return ,(@($exe) + $pyArgs)
}

function FindNmap {
  param([string]$requestedDir = "")
  if ($requestedDir) {
    if (-not (Test-Path -LiteralPath (Join-Path $requestedDir "nmap.exe"))) {
      Write-Host "[-] nmap.exe not found at $(Join-Path $requestedDir 'nmap.exe')" -ForegroundColor Red
      exit 1
    }
    if (-not (Test-Path -LiteralPath (Join-Path $requestedDir "scripts\script.db"))) {
      Write-Host "[-] script.db not found at $(Join-Path $requestedDir 'scripts\script.db')" -ForegroundColor Red
      exit 1
    }
    return $requestedDir
  }
  foreach ($path in "C:\Program Files (x86)\Nmap", "C:\Program Files\Nmap") {
    if ((Test-Path -LiteralPath (Join-Path $path "nmap.exe")) -and (Test-Path -LiteralPath (Join-Path $path "scripts\script.db"))) {
      return $path
    }
  }
  $cmd = Get-Command nmap.exe -ErrorAction SilentlyContinue
  if ($cmd) {
    $dir = Split-Path -Parent $cmd.Source
    if (Test-Path -LiteralPath (Join-Path $dir "scripts\script.db")) { return $dir }
  }
  Write-Host "[-] nmap.exe not found. Please install Nmap with Npcap, then run this script again." -ForegroundColor Red
  Write-Host "    You can search for Nmap with: winget search Nmap"
  exit 1
}

function ConvertTo-YamlQuoted {
  param([string]$text)
  return "'" + $text.Replace("'", "''") + "'"
}

function SetFolderPermissions {
  $userSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
  $allowed = @($userSid, "S-1-5-18", "S-1-5-32-544")
  $sidType = [System.Security.Principal.SecurityIdentifier]
  try {
    & icacls $PSScriptRoot /inheritance:r /grant:r "*${userSid}:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F"
    if ($LASTEXITCODE -ne 0) { throw "icacls failed with exit code $LASTEXITCODE" }
    # /grant:r only replaces the entries of these three accounts, so explicit entries for anyone else are removed here
    $others = @((Get-Acl -LiteralPath $PSScriptRoot).GetAccessRules($true, $true, $sidType) |
      Where-Object { $_.AccessControlType -eq 'Allow' -and $allowed -notcontains $_.IdentityReference.Value } |
      ForEach-Object { $_.IdentityReference.Value } | Select-Object -Unique)
    foreach ($sid in $others) {
      & icacls $PSScriptRoot /remove:g "*$sid"
      if ($LASTEXITCODE -ne 0) { throw "icacls could not remove $sid (exit code $LASTEXITCODE)" }
    }
    $left = @((Get-Acl -LiteralPath $PSScriptRoot).GetAccessRules($true, $true, $sidType) |
      Where-Object { $_.AccessControlType -eq 'Allow' -and $allowed -notcontains $_.IdentityReference.Value })
    if ($left.Count -gt 0) { throw "Found access for $($left[0].IdentityReference.Value)" }
    & icacls "$PSScriptRoot\*" /reset /T /C /Q
    if ($LASTEXITCODE -ne 0) { throw "icacls reset failed with exit code $LASTEXITCODE" }
  } catch {
    Write-Host "[-] Cannot set folder permissions: $_" -ForegroundColor Red
    Write-Host "    Consider cloning the repo into a folder owned by your user account."
    exit 1
  }
}

Write-Host "[+] Checking dependencies for Windows ..."
$pythonCmd = RequirePython
$pythonExe = $pythonCmd[0]
$pythonArgs = @($pythonCmd | Select-Object -Skip 1)
Write-Host "[+] Finding nmap installation ..."
$nmapDir = FindNmap -requestedDir $NmapDir
Write-Host "[+] Setting folder permissions before installing requirements ..."
SetFolderPermissions
Write-Host "[+] Installing Python requirements in .venv ..."
& $pythonExe @pythonArgs "-m" "venv" ".venv"
if ($LASTEXITCODE -ne 0) { exit 1 }
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit 1 }

$scriptsPath = Join-Path $nmapDir "scripts"
$filePath = Join-Path $scriptsPath "script.db"
$config = @"
config:
  scriptsPath: $(ConvertTo-YamlQuoted $scriptsPath)
  filePath: $(ConvertTo-YamlQuoted $filePath)
  fileBackup: 'scriptbk.db'
  scriptdb: 'nmap_scripts.sqlite3'
  categories: ["auth","broadcast","brute","default","discovery","dos","exploit","external","fuzzer","intrusive","malware","safe","version","vuln"]
  checksum: ''
"@
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot "config.yaml"), $config, [System.Text.UTF8Encoding]::new($false))

Write-Host "[+] NSEarch is ready. Run it with: .\.venv\Scripts\python.exe nsearch.py"
