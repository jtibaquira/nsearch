```
================================================
  _   _  _____  _____                     _
 | \ | |/  ___||  ___|                   | |
 |  \| |\ `--. | |__    __ _  _ __   ___ | |__
 | . ` | `--. \|  __|  / _` || '__| / __|| '_ \
 | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
 \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
================================================
 Version 0.3     |   @jjtibaquira
================================================
```
### Nmap Script Engine Search

### Description
#### nsearch , is a tool that helps you find scripts that are used nmap ( nse ) , can be searched using the name or category , it is also possible to see the documentation of the scripts found.

### Version
0.3

### Requeriments

```
$ pip install pyyaml python-i18n
```

#### Debian(Ubuntu)

```
# apt-get install unzip libreadline-gplv2-dev build-essential checkinstall unzip sqlite3 libsqlite3-dev -y
```

#### REDHAT(CentOS)

```
# yum -y install bzip2 groupinstall "Development Tools"
```

### Installation
#### To install the application is necessary run as root user the installation script (install.sh), for the time, the script is only for OS based on debian and based on Red Hat (CentOS). MacOSX or other UNIX  it's better do the installation for each dependency manually.

#### Automatic Installation

```
# sh install.sh
```

##### File Configuration
###### Find the script.db's path, use the command below
```
$ find /usr -type f -name "script.db" 2>/dev/null | awk 'gsub("script.db","")'
```
###### Then create a config.yaml file, on the main path of the script
```
config:
  scriptsPath: '/usr/local/share/nmap/scripts/'
  filePath: '/usr/local/share/nmap/scripts/script.db'
  fileBackup: 'scriptbk.db'
  scriptdb: 'nmap_scripts.sqlite3'
  categories: {"auth","broadcast","brute","default","discovery","dos","exploit","external","fuzzer","intrusive","malware","safe","version","vuln"}

```

### USAGE:

```
  $ python nsearch.py
```

#### Main Menu
#### Initial Setup

```
 ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_ \
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
 ================================================
   Version 0.3     |   @jjtibaquira
 ================================================

  Creating Database :nmap_scripts.sqlite3
  Creating Table For Script ....
  Creating Table for Categories ....
  Creating Table for Scripts per Category ....
  Upload Categories to Categories Table ...
```

#### Main Console

```
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.3     |   @jjtibaquira
  ================================================

  nsearch>
```

#### Basic Commands

```
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.3     |   @jjtibaquira
  ================================================

  nsearch> help

  Nsearch Commands
  ================
  clear  doc  exit  help  history  last  search

  nsearch>
```

```
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.3     |   @jjtibaquira
  ================================================

  nsearch> help search

  name     : Search by script's name
  category : Search by category
  Usage:
    search name:http
    search category:exploit

  nsearch>
```

```
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.3     |   @jjtibaquira
  ================================================

  nsearch> search name:ssh
  1.ssh-hostkey.nse
  2.ssh2-enum-algos.nse
  3.sshv1.nse
  nsearch>
```

```
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.3     |   @jjtibaquira
  ================================================

  nsearch> doc ssh <TAB>
  ssh-hostkey.nse      ssh2-enum-algos.nse  sshv1.nse
  nsearch> doc sshv1.nse
  local nmap = require "nmap"
  local shortport = require "shortport"
  local string = require "string"

  description = [[
    Checks if an SSH server supports the obsolete and less secure SSH Protocol Version 1.
  ]]
  author = "Brandon Enright"
  nsearch>
```


### TODO
* Fast-Tarck
* Searching by Author
* Serching by name, category, author in the same query
* Create a pretty output
* Create a file output
* Version for Windows
* Set like a favorite script

### FeedBack
#### Feel free to fork the project, submit any kind of comment, issue or contribution.

* Twitter: [@jjtibaquira](https://twitter.com/jjtibaquira)
* Email: jko@dragonjar.org
* Foro: http://comunidad.dragonjar.org