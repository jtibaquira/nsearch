#!/bin/bash
echo -e "\n"
echo "========================================";
echo " _   _  _____                     _     ";
echo "| \ | |/  ___|                   | |    ";
echo "|  \| |\ \`--.  ___  __ _ _ __ ___| |__  ";
echo "| . \` | \`--. \/ _ \/ _\` | '__/ __| '_ \ ";
echo "| |\  |/\__/ /  __/ (_| | | | (__| | | |";
echo "\_| \_/\____/ \___|\__,_|_|  \___|_| |_|";
echo "                                        ";
echo "========================================";
echo " Version 0.2     |   @jjtibaquira       ";
echo "========================================";
echo -e "\n"

homePath=$(pwd)
nmapversion=$(nmap -V 2>/dev/null)
luaversion=$(lua -v 2>/dev/null)
luarocks=$(luarocks 2>/dev/null)

#Check if is it root
if [ $EUID -ne 0 ]; then
 echo "You must be root."
 exit 1
fi

echo -e "Checking Dependencies ....\n"
apt-get install unzip libreadline-gplv2-dev build-essential checkinstall unzip sqlite3 libsqlite3-dev -y

function os_detection(){
  if [ -f /etc/lsb-release ]; then
    make install
  elif [ -f /etc/debian_version ]; then
    make install
  elif [ -f /etc/redhat-release ]; then
    echo "Please Follow the instructions into the Readme File"
  else
    echo "Please Follow the instructions into the Readme File"
  fi
}

function install_nmap(){
  echo "Installing nmap .... "
  cd /tmp; curl -R -O http://nmap.org/dist/nmap-6.47.tar.bz2; bzip2 -cd nmap-6.47.tar.bz2 | tar xvf -; cd nmap-6.47; ./configure; make; os_detection
}

function install_lua(){
  if [ -f /etc/lsb-release ]; then
    apt-get install lua5.2 liblua5.2-dev -y
  elif [ -f /etc/debian_version ]; then
    apt-get install lua5.2 liblua5.2-dev -y
  elif [ -f /etc/redhat-release ]; then
    echo "Please Follow the instructions into the Readme File"
  else
    echo "Please Follow the instructions into the Readme File"
  fi
}

function install_luarocks(){
  echo "Installing luarocks ..."
  cd /tmp; curl -O -R http://luarocks.org/releases/luarocks-2.2.0.tar.gz; tar xvzf luarocks-2.2.0.tar.gz; cd luarocks-2.2.0; ./configure --lua-version=5.2; os_detection

  if [ -f /etc/lsb-release ]; then
    luarocks install lsqlite3
  elif [ -f /etc/debian_version ]; then
    luarocks install lsqlite3
  elif [ -f /etc/redhat-release ]; then
    echo "Please Follow the instructions into the Readme File"
  else
    echo "Please Follow the instructions into the Readme File"
  fi
}

if [[ $nmapversion ]]; then
  echo -e "\nNmap already installed :D \n"
else
  while true; do
    echo -e "\n"
    read -p "Do you wish to install nmap? " yn
    case $yn in
      [Yy]* ) install_nmap; break;;
      [Nn]* ) break;;
      * ) echo "Please answer yes or no.";;
    esac
  done
fi

if [[ $luaversion ]]; then
  echo -e "Lua already installed :D \n"
else
  while true; do
    echo -e "\n"
    read -p "Do you wish to install lua? " yn
    case $yn in
      [Yy]* ) install_lua; break;;
      [Nn]* ) break;;
      * ) echo "Please answer yes or no.";;
    esac
  done
fi

if [[ $luarocks ]]; then
  echo -e "luarocks already installed :D \n\nNSEarch is ready for be launched uses lua nsearch.lua\n"
else
  while true; do
    echo -e "\n"
    read -p "Do you wish to install luarocks? " yn
    case $yn in
      [Yy]* ) install_luarocks;  break;;
      [Nn]* ) break;;
      * ) echo "Please answer yes or no.";;
    esac
  done
fi

dbpath=$(find /usr -type f -name "script.db" 2>/dev/null | awk 'gsub("script.db","")')
if [[ $dbpath ]]; then
  cd $homePath
  echo -e "local config = {} \n" > config.lua
  echo -e "config.scriptsPath='$dbpath'" >> config.lua
  echo -e "config.filePath = config.scriptsPath..'script.db'" >> config.lua
  echo -e "config.fileBackup = 'scriptbk.db'" >> config.lua
  echo -e "config.scriptdb = 'nmap_scripts.sqlite3'" >> config.lua
  echo -e 'config.categories = {"auth","broadcast","brute","default","discovery","dos","exploit","external","fuzzer","intrusive","malware","safe","version","vuln"}\n' >> config.lua
  echo -e "return config" >> config.lua
  chmod 777 config.lua
  rm -rf /tmp/lua*
  rm -rf /tmp/nmap-6.47*
fi