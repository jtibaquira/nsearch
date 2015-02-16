#!/bin/bash
echo "\n";
echo "========================================";
echo " _   _  _____                     _     ";
echo "| \ | |/  ___|                   | |    ";
echo "|  \| |\ \`--.  ___  __ _ _ __ ___| |__  ";
echo "| . \` | \`--. \/ _ \/ _\` | '__/ __| '_ \ ";
echo "| |\  |/\__/ /  __/ (_| | | | (__| | | |";
echo "\_| \_/\____/ \___|\__,_|_|  \___|_| |_|";
echo "                                        ";
echo "========================================";
echo " Version 0.3     |   @jjtibaquira       ";
echo "========================================";
echo "\n";



#Check if is it root
if ! [ $(id -u) = 0 ]; then
   echo "You must be a root user" 2>&1
   exit 1
fi

homePath=$(pwd)
nmapversion=$(nmap -V 2>/dev/null)
paythonversion=$(python -V)
pipversion=$(pip -V 2>/dev/null)

echo -e "Checking Dependencies ....\n"
apt-get install unzip libreadline-gplv2-dev build-essential checkinstall unzip sqlite3 libsqlite3-dev -y

function os_detection(){
  if [ -f /etc/lsb-release ]; then
    make install
  elif [ -f /etc/debian_version ]; then
    make install
  else
    echo "Please Follow the instructions into the Readme File"
  fi
}

function install_nmap(){
  echo "Installing nmap .... "
  cd /tmp; curl -R -O http://nmap.org/dist/nmap-6.47.tar.bz2; bzip2 -cd nmap-6.47.tar.bz2 | tar xvf -; cd nmap-6.47; ./configure; make; os_detection
}

function install_pyhon(){
  if [ -f /etc/lsb-release ]; then
    apt-get install python-dev -y
  elif [ -f /etc/debian_version ]; then
    apt-get install python-dev -y
  else
    echo "Please Follow the instructions into the Readme File"
  fi
}

function install_pip(){
  echo "Installing pip ..."

  if [ -f /etc/lsb-release ]; then
    apt-get install python-pip -y
    pip install sqlite3 yaml
  elif [ -f /etc/debian_version ]; then
    apt-get install python-pip -y
    pip install sqlite3 yaml
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

if [[ $paythonversion ]]; then
  echo -e "Python already installed :D \n"
else
  while true; do
    echo -e "\n"
    read -p "Do you wish to install python? " yn
    case $yn in
      [Yy]* ) install_pyhon; break;;
      [Nn]* ) break;;
      * ) echo "Please answer yes or no.";;
    esac
  done
fi

if [[ $pipversion ]]; then
  echo -e "Python already installed :D \n\nNSEarch is ready for be launched uses python nsearch.py\n"
else
  while true; do
    echo -e "\n"
    read -p "Do you wish to install pip? " yn
    case $yn in
      [Yy]* ) install_pip;  break;;
      [Nn]* ) break;;
      * ) echo "Please answer yes or no.";;
    esac
  done
fi

dbpath=$(find /usr -type f -name "script.db" 2>/dev/null | awk 'gsub("script.db","")')
if [[ $dbpath ]]; then
  cd $homePath
  echo -e "config: \n" > config.yaml
  echo -e "\tconfig.scriptsPath:'$dbpath'" >> config.yaml
  echo -e "\tconfig.filePath: config.scriptsPath..'script.db'" >> config.yaml
  echo -e "\tconfig.fileBackup: 'scriptbk.db'" >> config.yaml
  echo -e "\tconfig.scriptdb: 'nmap_scripts.sqlite3'" >> config.yaml
  echo -e '\tconfig.categories: {"auth","broadcast","brute","default","discovery","dos","exploit","external","fuzzer","intrusive","malware","safe","version","vuln"}\n' >> config.yaml
  chmod 777 config.yaml
  rm -rf /tmp/nmap-6.47*
fi