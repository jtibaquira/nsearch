#####   ================================================
#####     _   _  _____  _____                     _
#####    | \ | |/  ___||  ___|                   | |
#####    |  \| |\ `--. | |__    __ _  _ __   ___ | |__
#####    | . ` | `--. \|  __|  / _` || '__| / __|| '_ \
#####    | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
#####    \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
#####   ================================================
#####    Version 0.1     |   @jjtibaquira
#####   ================================================

# NSEarch
### Nmap Script Enginee Search

## Description
#### nsearch is a minimal script to help find a diferentes script into the nse database file

## Help Menu

### NSEarch (0.1)
#### USAGE:
##### nsearch
#### Main Menu:
##### 1 Help (h)
##### 2 Initial Setup (i)
##### 3 Search by Name of Script (s)
##### 4 Search by Category (c)
##### 5 Create script.db backup (b)
##### 6 Exit (q)
#### EXAMPLES:
#####  name:http
#####  category:exploit

### Pre-Requeriments
#### Debian(Ubuntu)
##### sudo apt-get install unzip libreadline-gplv2-dev build-essential checkinstall unzip sqlite3 libsqlite3-dev -y
#### REDHAT(CentOS)
##### #yum -y install bzip2 groupinstall "Development Tools"

### Installation
##### To install the application es necessary run as root the install script (install.sh), the script is only for OS based on debian, for OS based on REHL, MacOSX it's better do it manually.
#### Automatic Installation
##### # sh install.sh
#### Manual Installation
##### $ curl -R -O http://nmap.org/dist/nmap-6.47.tar.bz2
##### $ bzip2 -cd nmap-6.47.tar.bz2 | tar xvf -
##### $ cd nmap-6.47
##### $ ./configure && make
##### # make install
##### $ cd /tmp
##### $ curl -R -O http://www.lua.org/ftp/lua-5.3.0.tar.gz
##### $ tar zxvf lua-5.3.0.tar.gz -C $HOME/
##### $ cd $HOME/lua-5.3.0
##### $ make linux test
##### # ln -s $HOME/lua-5.3.0/src/lua /usr/local/bin/lua
##### $ cd /tmp
##### $ curl -O -R http://luarocks.org/releases/luarocks-2.2.0.tar.gz
##### $ tar xvzf luarocks-2.2.0.tar.gz
##### $ cd luarocks-2.2.0
##### $./configure --lua-version=5.3
##### # make install
##### # luarocks install lsqlite3

## TODO
* Fast-Tarck
* Searching by Author
* Create a pretty output
* Create a file output