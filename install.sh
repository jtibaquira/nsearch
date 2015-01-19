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
echo " Version 0.1     |   @jjtibaquira       ";
echo "========================================";
echo -e "\n"

homePath=$(pwd)
nmapversion=$(nmap -V 2>/dev/null)
luaversion=$(lua -v 2>/dev/null)
luarocks=$(luarocks 2>/dev/null)

function os_detection(){
  if [ -f /etc/lsb-release ]; then
    . /etc/lsb-release
    sudo make install
  elif [ -f /etc/debian_version ]; then
    make install
  elif [ -f /etc/redhat-release ]; then
    su - root -c "make install"
  else
    su - root -c "make install"
  fi
}

function install_nmap(){
  echo "Installing nmap .... "
  cd /tmp; curl -R -O http://nmap.org/dist/nmap-6.47.tar.bz2; bzip2 -cd nmap-6.47.tar.bz2 | tar xvf -; cd nmap-6.47; ./configure; make; os_detection
}

function install_lua(){
  if [ -f /etc/lsb-release ]; then
    sudo apt-get install lua5.2 liblua5.2-dev -y
  elif [ -f /etc/debian_version ]; then
    apt-get install lua5.2 liblua5.2-dev -y
  elif [ -f /etc/redhat-release ]; then
    su - root -c "yum install lua"
  else
    cd /tmp; curl -R -O http://www.lua.org/ftp/lua-5.3.0.tar.gz; tar zxvf lua-5.3.0.tar.gz -C $HOME/; cd $HOME/lua-5.3.0; make linux test;
    su root
    ln -s $HOME/lua-5.3.0/src/lua /usr/local/bin/lua
    logout
    source ~/.bashrc
    source ~/.profile
  fi
}

function install_luarocks(){
  echo "Installing luarocks ..."
  cd /tmp; curl -O -R http://luarocks.org/releases/luarocks-2.2.0.tar.gz; tar xvzf luarocks-2.2.0.tar.gz; cd luarocks-2.2.0; ./configure --lua-version=5.2; os_detection

  if [ -f /etc/lsb-release ]; then
    sudo luarocks install lsqlite3
  elif [ -f /etc/debian_version ]; then
    luarocks install lsqlite3
  elif [ -f /etc/redhat-release ]; then
    su - root -c "luarocks install lsqlite3"
  else
    cd /tmp; curl -R -O http://www.lua.org/ftp/lua-5.3.0.tar.gz; tar zxvf lua-5.3.0.tar.gz -C $HOME/; cd $HOME/lua-5.3.0; make linux test;
    su root
    ln -s $HOME/lua-5.3.0/src/lua /usr/local/bin/lua
    logout
    source ~/.bashrc
    source ~/.profile
  fi
}

if [[ $nmapversion ]]; then
  nmap -V 2>/dev/null
else
  while true; do
    read -p "Do you wish to install nmap? " yn
    case $yn in
      [Yy]* ) install_nmap; break;;
      [Nn]* ) break;;
      * ) echo "Please answer yes or no.";;
    esac
  done
fi

if [[ $luaversion ]]; then
  lua -v 2>/dev/null
else
  while true; do
    read -p "Do you wish to install lua? " yn
    case $yn in
      [Yy]* ) install_lua; break;;
      [Nn]* ) break;;
      * ) echo "Please answer yes or no.";;
    esac
  done
fi

if [[ $luarocks ]]; then
  luarocks 2>/dev/null
else
  while true; do
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
  echo $dbpath
  cd $homePath
  echo -e "local config = {} \n" > config.lua
  echo -e "config.scriptsPath='$dbpath'" >> config.lua
  echo -e "config.filePath = config.scriptsPath..'script.db'" >> config.lua
  echo -e "config.fileBackup = 'scriptbkp.db'" >> config.lua
  echo -e "config.scriptdb = 'nmap_scripts.sqlite3'" >> config.lua
  echo -e 'config.categories = {"auth","broadcast","brute","default","discovery","dos","exploit","external","fuzzer","intrusive","malware","safe","version","vuln"}\n' >> config.lua
  echo -e "return config" >> config.lua
  chmod 777 config.lua
  rm -rf /tmp/lua*
  rm -rf /tmp/nmap-6.47*
fi