```bash
================================================
  _   _  _____  _____                     _
 | \ | |/  ___||  ___|                   | |
 |  \| |\ `--. | |__    __ _  _ __   ___ | |__
 | . ` | `--. \|  __|  / _` || '__| / __|| '_ \
 | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
 \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
================================================
 Version 0.1     |   @jjtibaquira
================================================
```
### Nmap Script Enginee Search

## Description
#### nsearch is a minimal script to help find a diferentes script into the nse database file

### Pre-Requeriments
#### Debian(Ubuntu)
##### sudo apt-get install unzip libreadline-gplv2-dev build-essential checkinstall unzip sqlite3 libsqlite3-dev -y
#### REDHAT(CentOS)
##### #yum -y install bzip2 groupinstall "Development Tools"

### Installation
##### To install the application es necessary run as root the install script (install.sh), the script is only for OS based on debian, for OS based on REHL, MacOSX it's better do it manually.
#### Automatic Installation
```bash
# sh install.sh
```
#### Manual Installation
##### Nmap Installation
```bash
$ curl -R -O http://nmap.org/dist/nmap-6.47.tar.bz2
$ bzip2 -cd nmap-6.47.tar.bz2 | tar xvf -
$ cd nmap-6.47
$ ./configure && make
# make install
```
##### Lua Installation
```bash
$ cd /tmp
$ curl -R -O http://www.lua.org/ftp/lua-5.3.0.tar.gz
$ tar zxvf lua-5.3.0.tar.gz -C $HOME/
$ cd $HOME/lua-5.3.0
$ make linux test
# ln -s $HOME/lua-5.3.0/src/lua /usr/local/bin/lua
```
##### Luarocks Installation
```bash
$ cd /tmp
$ curl -O -R http://luarocks.org/releases/luarocks-2.2.0.tar.gz
$ tar xvzf luarocks-2.2.0.tar.gz
$ cd luarocks-2.2.0
$./configure --lua-version=5.3
# make install
# luarocks install lsqlite3
```

### NSEarch (0.1)
#### USAGE:
##### Main Menu
```bash
 ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_ \
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.1     |   @jjtibaquira
  ================================================

    1 Help (h)
    2 Initial Setup (i)
    3 Search Script (s)
    4 Create script.db backup (b)
    5 Exit (q)

 What do you want to do? :
```

#### Initial Setup(option 2)
```bash
 ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_ \
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
 ================================================
   Version 0.1     |   @jjtibaquira
 ================================================

Creating Database :nmap_scripts.sqlite3
Creating Table For Script ....
Creating Table for Categories ....
Creating Table for Scripts per Category ....
Upload Categories to Categories Table ...
```

#### Search by Name(option 3)
```bash
 ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_ \
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.1     |   @jjtibaquira
  ================================================

    name : search by script's name
    category : search by category
    exit : close the console
    back : returns to the main menu

     Usage:

       name:http

       category:exploit
    nsearch>
```

```bash
   ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_ \
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.1     |   @jjtibaquira
  ================================================

  nsearch> name:http

  Total Scripts Found 101

    1 http-adobe-coldfusion-apsa1301.nse
    2 http-affiliate-id.nse
    3 http-apache-negotiation.nse
    4 http-auth-finder.nse
    5 http-auth.nse
    6 http-awstatstotals-exec.nse
    7 http-axis2-dir-traversal.nse
    8 http-backup-finder.nse
    9 http-barracuda-dir-traversal.nse
    .
    .
    .
    100 membase-http-info.nse
    101 riak-http-info.nse

    Do yo want more info about any script, choose the script using id [1-101] or quit (0) 1

    description = [[
    Attempts to exploit an authentication bypass vulnerability in Adobe Coldfusion servers (APSA13-01: http://www.adobe.com/support/security/advisories/apsa13-01.html) to retrieve a valid administrator's session cookie.
    ]]

    ---
    -- @usage nmap -sV --script http-adobe-coldfusion-apsa1301 <target>
    -- @usage nmap -p80 --script http-adobe-coldfusion-apsa1301 --script-args basepath=/cf/adminapi/ <target>
    --
    -- @output
    -- PORT   STATE SERVICE
    -- 80/tcp open  http
    -- | http-adobe-coldfusion-apsa1301:
    -- |_  admin_cookie: aW50ZXJhY3RpdmUNQUEyNTFGRDU2NzM1OEYxNkI3REUzRjNCMjJERTgxOTNBNzUxN0NEMA1jZmFkbWlu
    --
    -- @args http-adobe-coldfusion-apsa1301.basepath URI path to administrator.cfc. Default: /CFIDE/adminapi/
    --
    ---

    author = "Paulino Calderon <calderon@websec.mx>"

    Do yo want more info about any script, choose the script using id [1-101] or quit (0)
```

## TODO
* Fast-Tarck
* Searching by Author
* Serching by name, category, author in the same query
* Create a pretty output
* Create a file output