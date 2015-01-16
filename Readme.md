# NSEarch

## Description
#### nsearch is a minimal script to help find a diferentes script into the nse database file

## Help Menu

### NSEarch (0.1)
#### USAGE:
##### nsearch [Options] string
#### PARAMETERS:
#####  -s  create the initial scriptdb for future queries
#####  -h  Display this help menu
#####  -n  The string to search
#####  -c  Get all script into a category
#####  -b  Create a script.db backup for future diff default name scriptbkp.db the files name are defined in config.lua
#### EXAMPLES:
#####  nsearch -n http
#####  nsearch -c exploit
#####  nsearch -s

### Pre-Requeriments
#### Debian(Ubuntu)
##### sudo apt-get install libreadline-gplv2-dev build-essential checkinstall unzip sqlite3 libsqlite3-dev -y
#### REDHAT(CentOS)
##### #yum -y install bzip2 groupinstall "Development Tools"

## TODO
* Searching for Category
* Create a backup option
* Searching by Author
* Create a pretty output
* Create a file output