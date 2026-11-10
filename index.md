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

### Nmap Scripting Engine Search

NSEarch helps you find the scripts used by nmap (NSE). You can search by name, category, and author, or combine all three in a single query. You can also read a script's documentation, keep a list of favorites, run nmap with predefined templates, and run workflows: chains of scans where each stage only scans what earlier stages found, with reports you can save and compare.

This page is a summary. The [README](https://github.com/jtibaquira/nsearch#readme) has the full documentation.

### Requirements

- Python 3.12 or later
- nmap

On Windows 10/11, install Python 3.12 or later and the official Nmap installer, including Npcap.

### Installation

The install script supports Debian, Ubuntu, Red Hat, Fedora, CentOS, and macOS. It places the Python dependencies in a local virtual environment. On Linux, it uses `sudo` to install system packages.

```
$ git clone https://github.com/jtibaquira/nsearch.git
$ cd nsearch
$ bash install.sh
$ .venv/bin/python nsearch.py
```

On Windows 10/11, run PowerShell from the project directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

If Nmap is installed in a different directory, pass its path with `-NmapDir`:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -NmapDir 'D:\Tools\Nmap'
```

Run NSEarch with the virtual environment's Python:

```powershell
.\.venv\Scripts\python.exe nsearch.py
```

The first run creates the local database. Later runs rebuild it only when nmap's `script.db` changes, and your favorites are kept.

The [README](https://github.com/jtibaquira/nsearch#manual-installation) explains how to install it manually.

### Searching for scripts

```
nsearch> search name:http author:calderon category:vuln
*** Name                                     Author
[+] http-adobe-coldfusion-apsa1301.nse       Paulino Calderon <calderon@websec.mx>
[+] http-avaya-ipoffice-users.nse            Paulino Calderon <calderon@websec.mx>
[+] http-awstatstotals-exec.nse              Paulino Calderon <calderon@websec.mx>
...

nsearch> doc sshv1.nse
description = [[
Checks if an SSH server supports the obsolete and less secure SSH Protocol Version 1.
]]
author = "Brandon Enright"
```

### Favorites

```
nsearch> addfav name:http-vuln-cve2012-1823.nse ranking:great
[+] http-vuln-cve2012-1823.nse The script was added successfully

nsearch> showfav
*** Name                                     Ranking
[+] http-vuln-cve2012-1823.nse               great
```

Use `modfav` to change a ranking and `delfav` to remove a script.

### Scanning

**Only scan systems that you own or are explicitly authorized to test.**

`run` scans a target with one of the templates: `ping`, `default`, `http`, or `ssh`. Templates without scripts, or with selectors that choose only `safe` scripts (without `external` or `not`), start without confirmation. Other unblocked selectors ask `[y/N]` before the scanner is created. Scripts in the `dos` and `broadcast` categories are always rejected in templates. The `http` template excludes `brute`, `dos`, `exploit`, `fuzzer`, and `external`; it still includes scripts outside `safe`, so it asks for confirmation.

```
nsearch> run template:ping net:127.0.0.1
```

### Workflows

A workflow is a chain of scans. Each stage only scans what earlier stages found. NSEarch includes `hosts`, `basic`, `allports`, `defaults`, `tls`, `web`, `ssh`, `smb`, `ftp`, `mail`, `database`, `remote`, and `vuln`. The `web` and `vuln` workflows check for known vulnerabilities without scripts that exploit them or query third parties, and both ask for confirmation. You can add your own workflows in the `workflows` directory.

```
nsearch> workflow list
nsearch> workflow run name:basic net:127.0.0.1
nsearch> workflow status id:1
nsearch> workflow resume id:1
nsearch> workflow report id:1 format:md
nsearch> workflow compare id:1 with:2
nsearch> workflow suggest id:1
```

| Command | What it does |
|---|---|
| `run` | Shows the plan and asks for confirmation before it starts |
| `status` | Lists the runs, or shows the results of one |
| `resume` | Continues a run that was interrupted or failed |
| `report` | Saves a Markdown or JSON report that only your user can read |
| `compare` | Shows what changed between two runs |
| `suggest` | Lists `safe` scripts for the services found, and runs only the ones you pick |

- **Confirmation:** stages that can be intrusive ask first, and show the hosts and ports they will scan.
- **Scope:** only an allowed set of nmap options is accepted, and stages after the first only scan hosts found by the first stage. Data from scanned hosts is never used to build nmap arguments.
- **Blocked scripts:** `dos` and `broadcast` scripts never run in a workflow.
- **Warnings:** a run that stops seeing a host or port, or where nmap gives up on a host because of `--host-timeout`, ends as `completed_with_warnings`. These runs cannot be resumed or suggested from. NSEarch cannot tell a scan being blocked from a real change, so it does not say which one it was, and it never retries or slows down on its own.
- **Limits:** workflows use TCP only, and the included ones look at nmap's 1000 most common ports.

### TODO

* GUI
* Fast-Track
* Create file output for `run`

### Feedback

Feel free to fork the project and to submit comments, issues, or contributions.

* Twitter: [@jjtibaquira](https://twitter.com/jjtibaquira)
* Email: jacobotibaquira@gmail.com
