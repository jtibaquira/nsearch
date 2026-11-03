```
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.4b  https://github.com/jtibaquira/nsearch  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================
```

# Nmap Scripting Engine Search

## Description

NSEarch helps you find the scripts used by nmap (NSE). You can search by name, category, and author, or combine all three in a single query. You can also read a script's documentation, keep a list of favorites, and run nmap with predefined templates.

## Version

0.4b

## Requirements

- Python 3.9 or later
- nmap

The Python dependencies are listed in `requirements.txt`. The install script places them in a local virtual environment.

## Installation

### Automatic installation

The script supports Debian, Ubuntu, Red Hat, Fedora, CentOS, and macOS. On Linux, it uses `sudo` to install system packages.

```
$ bash install.sh
```

Use `bash`, not `sh`: the script does not run under `sh`.

### Manual installation

Install nmap and Python 3, then create the virtual environment:

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
addfav  delfav  exit  history  modfav  search
```

```
nsearch> help search

    name     : Search by script's name
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

## Tests

```
$ .venv/bin/pip install -r requirements-dev.txt
$ .venv/bin/python -m pytest
```

## TODO

* GUI
* Fast-Track
* Create sequences for running scripts
* Create file output
* Windows version

## Feedback

Feel free to fork the project and to submit comments, issues, or contributions.

* Twitter: [@jjtibaquira](https://twitter.com/jjtibaquira)
* Email: jko@dragonjar.org
* Blog: https://www.dragonjar.org
* Forum: http://comunidad.dragonjar.org
* YouTube: https://www.dragonjar.tv
* Academic: https://www.dragonjar.education
