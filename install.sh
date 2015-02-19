#!/bin/bash
printf "\n"
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
printf "\n"



#Check if is it root
if ! [ $(id -u) = 0 ]; then
   echo "You must be a root user" 2>&1
   exit 1
fi

homePath=$(pwd)
nmapversion=$(which nmap 2>/dev/null)
paythonversion=$(which python 2>/dev/null)
pipversion=$(which pip 2>/dev/null)

printf "Checking Dependencies ....\n"
if [ -f /etc/lsb-release ] || [ -f /etc/debian_version ] ; then
  apt-get install unzip libreadline-gplv2-dev build-essential checkinstall unzip sqlite3 libsqlite3-dev -y
elif [ -f /etc/redhat-release ]; then
  yum install zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel -y
else
  echo "Please Follow the instructions into the Readme File"
fi


function install_nmap(){
  echo "Installing nmap .... "
  if [ -f /etc/lsb-release ] || [ -f /etc/debian_version ] ; then
    apt-get install nmap -y
  elif [ -f /etc/redhat-release ]; then
    yum install nmap -y
  else
    echo "Please Follow the instructions into the Readme File"
  fi
}

function install_pyhon(){
  echo "Installing python ..."
  if [ -f /etc/lsb-release ] || [ -f /etc/debian_version ] ; then
    apt-get install python -y
  elif [ -f /etc/redhat-release ]; then
    yum install python -y
  else
    echo "Please Follow the instructions into the Readme File"
  fi
}

function install_pip(){
  echo "Installing pip ..."

  if [ -f /etc/lsb-release ] || [ -f /etc/debian_version ]; then
    apt-get install python-pip -y; pip install PyYAML python-i18n
  elif [ -f /etc/redhat-release ]; then
    rpm -iUvh http://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm; yum -y update; yum -y install python-pip; pip install PyYAML python-i18n
  else
    echo "Please Follow the instructions into the Readme File"
  fi
}

if [[ $nmapversion ]]; then
  printf "\nNmap already installed :D \n"
else
  while true; do
    printf "\n"
    read -p "Do you wish to install nmap? " yn
    case $yn in
      [Yy]* ) install_nmap; break;;
      [Nn]* ) break;;
      * ) echo "Please answer yes or no.";;
    esac
  done
fi

if [[ $paythonversion ]]; then
  printf "Python already installed :D \n"
else
  while true; do
    printf "\n"
    read -p "Do you wish to install python? " yn
    case $yn in
      [Yy]* ) install_pyhon; break;;
      [Nn]* ) break;;
      * ) echo "Please answer yes or no.";;
    esac
  done
fi

if [[ $pipversion ]]; then
  pip install PyYAML python-i18n
  printf "Python already installed :D \n\nNSEarch is ready for be launched uses python nsearch.py\n"
else
  while true; do
    printf "\n"
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
  filePath=$dbpath'script.db'
  cd $homePath
  printf "config: \n" > config.yaml
  printf "  scriptsPath: '$dbpath'\n" >> config.yaml
  printf "  filePath: '$filePath'\n" >> config.yaml
  printf "  fileBackup: 'scriptbk.db'\n" >> config.yaml
  printf "  scriptdb: 'nmap_scripts.sqlite3'\n" >> config.yaml
  printf '  categories: {"auth","broadcast","brute","default","discovery","dos","exploit","external","fuzzer","intrusive","malware","safe","version","vuln"}\n' >> config.yaml
  chmod 777 config.yaml
fi