```
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================
```
### Nmap Scripting Engine Search

### Description
#### Nsearch, is a tool that helps you to find scripts that are used by nmap ( nse ) , you can search the scripts using differents keyword as the name, category and author, even using all the keyword in a single query,it is also possible to see the documentation of the scripts founded.

### Version
0.4b
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
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
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
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================

  Cheking DB ... nmap_scripts.sqlite3
  The DB is updated nmap_scripts.sqlite3

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
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================

  nsearch> help

  Nsearch Commands
  ================
  addfav  clear  delfav  doc  exit  help  history  last  modfav  search showfav

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
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================

  nsearch> help search

    name     : Search by script's name
    category : Search by category
    author   : Search by author
    Usage:
      search name:http
      search category:exploit
      search author:fyodor
      search name:http category:exploit author:fyodor

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
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================

  nsearch> search name:http author:calderon category:vuln
  *** Name                                     Author
  [+] http-vuln-cve2012-1823.nse               Paulino Calderon, Paul AMAR
  [+] http-phpself-xss.nse                     Paulino Calderon
  [+] http-wordpress-enum.nse                  Paulino Calderon
  [+] http-adobe-coldfusion-apsa1301.nse       Paulino Calderon
  [+] http-vuln-cve2013-0156.nse               Paulino Calderon
  [+] http-awstatstotals-exec.nse              Paulino Calderon
  [+] http-axis2-dir-traversal.nse             Paulino Calderon
  [+] http-huawei-hg5xx-vuln.nse               Paulino Calderon
  [+] http-tplink-dir-traversal.nse            Paulino Calderon
  [+] http-trace.nse                           Paulino Calderon
  [+] http-litespeed-sourcecode-download.nse   Paulino Calderon
  [+] http-majordomo2-dir-traversal.nse        Paulino Calderon
  [+] http-method-tamper.nse                   Paulino Calderon
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
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
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

#### Favorites Feature

```
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================

  nsearch> addfav name:http-vuln-cve2012-1823.nse ranking:great
  [+] http-vuln-cve2012-1823.nse The Script was added successfully
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
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================

  nsearch> showfav
  *** Name                                     Ranking
  [+] sslv2.nse                                normal
  [+] http-vuln-cve2012-1823.nse               great
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
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================

  nsearch> showfav
  *** Name                                     Ranking
  [+] sslv2.nse                                normal
  [+] http-vuln-cve2012-1823.nse               great

  nsearch> modfav name:sslv2.nse newranking:great
  [+] sslv2.nse The Script was updated successfully

  nsearch> showfav
  *** Name                                     Ranking
  [+] sslv2.nse                                great
  [+] http-vuln-cve2012-1823.nse               great
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
   Version 0.4b http://goo.gl/8mFHE5  @jjtibaquira
   Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================

  nsearch> showfav
  *** Name                                     Ranking
  [+] sslv2.nse                                great
  [+] http-vuln-cve2012-1823.nse               great

  nsearch> delfav name:sslv2.nse
  [+] sslv2.nse The Script was removed successfully

  nsearch> showfav
  *** Name                                     Ranking
  [+] http-vuln-cve2012-1823.nse               great

  nsearch>
```

### TODO
* GUI
* Fast-Track
* Create sequences for the execution of scripts
* Create a file output
* Version for Windows

### FeedBack
#### Feel free to fork the project, submit any kind of comment, issue or contribution.

* Twitter: [@jjtibaquira](https://twitter.com/jjtibaquira)
* Email: jko@dragonjar.org
* Blog: https://www.dragonjar.org
* Foro: http://comunidad.dragonjar.org
* YouTube: https://www.dragonjar.tv
* Academic: https://www.dragonjar.education