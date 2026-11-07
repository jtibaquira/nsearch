```
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.5b  https://github.com/jtibaquira/nsearch  @jjtibaquira
   Email: jacobotibaquira@gmail.com
  ================================================
```

# Nmap Scripting Engine Search

## Description

NSEarch helps you find the scripts used by nmap (NSE). You can search by name, category, and author, or combine all three in a single query. You can also read a script's documentation, keep a list of favorites, run nmap with predefined templates, and run workflows: chains of scans where each stage only scans what earlier stages found, with reports you can save and compare.

## Version

0.5b

## Requirements

- Python 3.12 or later. It is the oldest version with at least one more year of security support, until October 2028
- nmap

On Windows 10/11, install Python 3.12 or later and the official Nmap installer, including Npcap. The Windows installer accepts either the Python launcher (`py -3`) or `python`.

The Python dependencies are listed in `requirements.txt`. The install script places them in a local virtual environment.

## Installation

Get the code first:

```
$ git clone https://github.com/jtibaquira/nsearch.git
$ cd nsearch
```

### Automatic installation

The script supports Debian, Ubuntu, Red Hat, Fedora, CentOS, and macOS. On Linux, it uses `sudo` to install system packages.

```
$ bash install.sh
```

Use `bash`, not `sh`: under `sh`, the script stops and asks you to run it with `bash`.

### Windows 10/11 installation

Run PowerShell from the project directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

The installer creates `.venv` and `config.yaml`. If Nmap is installed in a different directory, pass its installation path with `-NmapDir`:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -NmapDir 'D:\Tools\Nmap'
```

NSEarch runs the `nmap.exe` in the folder above `scriptsPath`, or the one in a standard Nmap install folder. It never runs an `nmap.exe` from `PATH` or from the current folder.

The installer restricts the project folder to your account, `SYSTEM`, and `Administrators`. New files and folders inside it, including the configuration and the SQLite database, inherit those permissions, while `reports` gets its own ACL restricted to your account as owner, `SYSTEM`, and `Administrators`. It does not request or need Administrator privileges. If it cannot apply the permissions, it stops and advises you to clone the project into a folder you own.

In `config.yaml`, quote Windows paths with single quotes. Do not put a trailing slash on `scriptsPath`:

```yaml
config:
  scriptsPath: 'C:\Program Files (x86)\Nmap\scripts'
  filePath: 'C:\Program Files (x86)\Nmap\scripts\script.db'
```

Run NSEarch with the virtual environment's Python:

```powershell
.\.venv\Scripts\python.exe nsearch.py
```

Without Administrator privileges, nmap uses a connect scan (`-sT`), as it does without root on Unix. The included templates and workflows do not use `-sS`, `-O`, `-sU`, or `-A`.

The Windows console does not provide readline, so Tab autocompletion is unavailable. NSEarch enables ANSI colors at startup; older consoles that do not support them may show the color codes as text. Windows Terminal is recommended.

If you press Ctrl+C during a workflow, nmap is stopped. Use `workflow resume id:<id>` to continue with the saved results; see [Workflows](#workflows) for resume behavior.

### Manual installation

Install nmap and Python 3.12 or later, then create the virtual environment:

```
$ python3 -m venv .venv
$ .venv/bin/pip install -r requirements.txt
```

Find the path to `script.db`:

```
$ find /usr /opt -type f -name script.db 2>/dev/null
```

Copy `config.yaml.example` to `config.yaml` in the main directory of the project, and set the paths you found:

```
config:
  scriptsPath: '/usr/share/nmap/scripts/'
  filePath: '/usr/share/nmap/scripts/script.db'
  fileBackup: 'scriptbk.db'
  scriptdb: 'nmap_scripts.sqlite3'
  categories: ["auth","broadcast","brute","default","discovery","dos","exploit","external","fuzzer","intrusive","malware","safe","version","vuln"]
  checksum: ''
```

## Usage

```
$ .venv/bin/python nsearch.py
```

The first run creates the local database. Later runs rebuild it only when nmap's `script.db` changes, and your favorites are kept.

### Basic commands

```
nsearch> help

Nsearch Commands
================
EOF     clear   doc   help     last    run     showfav
addfav  delfav  exit  history  modfav  search  workflow
```

```
nsearch> help search

    name     : Name of the script
    category : Search by category
    author   : Search by author
    Usage:
      search name:http
      search category:exploit
      search author:fyodor
      search name:http category:exploit author:fyodor
```

### Searching for scripts

Results are sorted by name. Use quotes when a value contains spaces, such as `search author:"Paulino Calderon"`.

```
nsearch> search name:http author:calderon category:vuln
*** Name                                     Author
[+] http-adobe-coldfusion-apsa1301.nse       Paulino Calderon <calderon@websec.mx>
[+] http-avaya-ipoffice-users.nse            Paulino Calderon <calderon@websec.mx>
[+] http-awstatstotals-exec.nse              Paulino Calderon <calderon@websec.mx>
...
```

Use `last` to display the most recent results again.

### Reading a script's documentation

`doc` accepts the script name with or without `.nse`. Press TAB to autocomplete from the last results.

```
nsearch> doc sshv1.nse
description = [[
Checks if an SSH server supports the obsolete and less secure SSH Protocol Version 1.
]]
author = "Brandon Enright"
license = "Same as Nmap--See https://nmap.org/book/man-legal.html"
categories = {"default", "safe"}
```

### Favorites

```
nsearch> addfav name:http-vuln-cve2012-1823.nse ranking:great
[+] http-vuln-cve2012-1823.nse The script was added successfully

nsearch> addfav name:sslv2.nse
[+] sslv2.nse The script was added successfully

nsearch> showfav
*** Name                                     Ranking
[+] http-vuln-cve2012-1823.nse               great
[+] sslv2.nse                                normal

nsearch> modfav name:sslv2.nse newranking:great
[+] sslv2.nse The script was updated successfully

nsearch> delfav name:sslv2.nse
[+] sslv2.nse The script was removed successfully
```

`showfav` also accepts filters, such as `showfav ranking:great` or `showfav name:http ranking:great`.

### Running nmap with templates

**Only scan systems that you own or are explicitly authorized to test.**

`run` requires a target and a template. The target can be a host name, an IP address, or a network range.

```
nsearch> run template:ping net:127.0.0.1
Running scan
----------------------------------------------------
Host : 127.0.0.1 (localhost)
State : up
```

The templates are in the `templates` directory:

| Template | What it does |
|---|---|
| `ping` | Checks whether hosts are up, without scanning ports |
| `default` | Detects services on ports 1-5000 |
| `http` | Runs the `http-*` scripts, except `http-slowloris` and `http-brute` |
| `ssh` | Lists the algorithms supported by SSH servers |

`run` starts the scan without asking for confirmation. The `http` template includes intrusive and brute-force scripts, so only use it where those are allowed. Workflows ask before intrusive stages.

### Workflows

**Only scan systems that you own or are explicitly authorized to test.**

A workflow is a chain of scans. Each stage only scans what earlier stages found, so a network is scanned once and then only the discovered hosts and ports are examined further.

```
nsearch> workflow list
[+] allports
[+] basic
[+] database
[+] defaults
[+] ftp
[+] hosts
[+] mail
[+] remote
[+] smb
[+] ssh
[+] tls
[+] vuln
[+] web

nsearch> workflow run name:basic net:127.0.0.1
nsearch> workflow status
nsearch> workflow status id:1
nsearch> workflow resume id:1
nsearch> workflow report id:1 format:md
nsearch> workflow compare id:1 with:2
nsearch> workflow suggest id:1
```

`workflow run` shows the plan and asks for confirmation before it starts. Results are stored in the local database.

If a workflow is interrupted or fails, use `workflow resume id:<id>` to continue from where it stopped. It works on runs with status `running`, `interrupted`, or `failed`:

- It shows the target and the remaining stages, and asks for confirmation again. Stages with `confirm` ask again too.
- Stages that were completed, skipped, or not confirmed do not run again. An unfinished stage runs again from its first target, and results already saved from it are kept.
- It uses the original target and scope, and rejects the run if the target is no longer valid.
- It rejects the run if the workflow file is no longer valid, or if anything in its stages changed: names, order, arguments, `from`, `when`, `confirm`, or `host_timeout`.
- A run with status `running` may belong to a console that is still working, so check that before you confirm.

`workflow report id:<id>` writes a report of any run to `reports/workflow-<id>.md`, or to `reports/workflow-<id>.json` with `format:json`. For each stage, it says why it ran, or why it did not, and what it scanned. Reports can contain sensitive results, so only your user can read them, and a `reports` folder that is a symbolic link is rejected. Writing a report again replaces the previous one. Runs from earlier versions do not have the targets or the reasons of their stages, so their reports say they were not recorded.

`workflow compare id:<id> with:<id>` shows what changed from the first run to the second: hosts, open ports, services, and script results. It warns you if the runs used a different workflow or target, or did not finish every stage, because in those cases a missing result may just not have been scanned. Runs with suggested stages count as having different stages.

`workflow suggest id:<id>` lists scripts for the services found by a completed run, and runs only the ones you pick:

- It only suggests scripts in the `safe` category that have not already run in that run. Suggestions are based on the script name, so nmap may decide that a script does not apply to a service.
- `safe` is nmap's own label, and it includes scripts that query third-party services, such as `http-virustotal`. Use `doc` to read a script before you pick it.
- For each service, it shows where the scripts would run and asks which ones you want. The default is none. It then shows the plan and asks for authorization before it scans.
- It only scans the hosts and ports of that service in that run. Each approved set is added to the run as a new stage, and appears in its status and report.
- If a suggested stage is interrupted or fails, the run stays `completed`, what was saved is kept, and `workflow suggest` offers the scripts again.

A run that stops seeing something it found ends with status `completed_with_warnings`, and its status and reports say what happened. This covers a port that was open and a later stage sees as filtered or closed, or does not report, a host that stops answering, and a port that the previous comparable run of the same target saw and this one did not. NSEarch cannot tell a scan being blocked from a real change, so a warning does not say which one it was:

- Hosts and ports that were not seen again are not scanned by later stages, and the stages left without targets are skipped.
- NSEarch never retries or slows down a scan on its own. If you want to check again, start a new run later.
- These runs cannot be resumed, and `workflow suggest` does not work on them, because they may not have seen everything. `workflow compare` works, and warns you.
- A previous run is only comparable if it finished and looked for ports in the same way. A port that really closed is only reported by the first run after it.
- A single run where a host answers and shows no open ports gives no warning, because that is also what a host with nothing exposed looks like.

These workflows are included:

| Workflow | Use it to | Stages after finding services |
|---|---|---|
| `hosts` | See which hosts are up. It does not scan ports | None, it only runs discovery |
| `basic` | List the services on the 1000 most common ports | None |
| `allports` | Find services on any TCP port. It is slower, and allows 60 minutes per host in each stage | None, but it looks at ports 1-65535 |
| `defaults` | Run nmap's `default` scripts, like `nmap -sC`, without the ones that query third parties | `default_scripts` (`confirm`) |
| `tls` | Check certificates and known TLS problems | `tls_info`, then `tls_ciphers` with `ssl-enum-ciphers` (`confirm`), because it opens many connections |
| `web` | Examine HTTP and HTTPS services | `http_enum`, then `http_vuln` (`confirm`) |
| `ssh` | Read SSH host keys and algorithms | `ssh_enum` |
| `smb` | Read information from SMB services | `smb_enum` |
| `ftp` | Check FTP anonymous access and server information | `ftp_enum` |
| `mail` | Read the capabilities of SMTP, IMAP, and POP3 services | `mail_enum` |
| `database` | Read information from MySQL, SQL Server, MongoDB, and Redis | `db_enum` |
| `remote` | Read information from RDP, VNC, and Telnet | `remote_enum` |
| `vuln` | Check every service found for known vulnerabilities, without scripts that exploit them or query third parties | `vuln_scripts` (`confirm`) |

A stage skips hosts that do not have its services. Workflows use nmap's scripts, so a result shows what the script reported, and not a verified vulnerability.

The workflows are in the `workflows` directory:

```yaml
web:
  stages:
    - name: discovery
      arguments: "-sn"
    - name: ports
      from: live_hosts
      arguments: "--top-ports 1000"
    - name: services
      from: open_ports
      arguments: "-sV"
    - name: http_enum
      from: services
      when: {service: [http, https]}
      arguments: "--script http-headers,http-title"
    - name: http_vuln
      from: services
      when: {service: [http, https]}
      arguments: "--script vuln"
      confirm: true
```

| Key | Meaning |
|---|---|
| `from` | What the stage scans: `live_hosts`, `open_ports`, or `services`. Only the first stage has no `from`, and it scans the target you gave. |
| `when` | With `from: services`, limits the stage to these service names. These stages always use version detection (`-sV`), so scripts also work on services on other ports. |
| `confirm` | Asks before running the stage. Required for any script that is not in the `safe` category, and for any script expression that uses `not`. |
| `host_timeout` | Maximum time per host. The default is 15 minutes. |

Safety rules:

- Only an allowed set of nmap options is accepted, so a workflow cannot add targets or read and write files.
- Stages after the first only scan hosts found by the first stage. Results outside that scope are ignored.
- Data from scanned hosts is never used to build nmap arguments.
- `dos` and `broadcast` scripts never run. They are excluded from every script expression, even in confirmed stages.

Workflows use TCP only. Except for `allports`, the included workflows look at nmap's 1000 most common ports, so services on other ports are not found. Without root privileges, nmap uses a connect scan, and OS detection (`-O`) is not available.

## Tests

```
$ .venv/bin/pip install -r requirements-dev.txt
$ .venv/bin/python -m pytest
$ .venv/bin/ruff check .
$ .venv/bin/mypy .
```

On Windows, run the checks with the virtual environment's Python and executables:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe .
```

## TODO

* GUI
* Fast-Track
* Create file output for `run`

## Feedback

Feel free to fork the project and to submit comments, issues, or contributions.

* Twitter: [@jjtibaquira](https://twitter.com/jjtibaquira)
* Email: jacobotibaquira@gmail.com
