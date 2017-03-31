#!/usr/bin/env bash
printf "\n"
echo "=================================================";
echo " _   _  _____  _____                     _     ";
echo "| \ | |/  ___||  ___|                   | |    ";
echo "|  \| |\ \`--. | |__    __ _  _ __   ___ | |__  ";
echo "| . \` | \`--. \|  __|  / _\` || '__| / __|| '_ \ ";
echo "| |\  |/\__/ /| |___ | (_| || |   | (__ | | | |";
echo "\_| \_/\____/ \____/  \__,_||_|    \___||_| |_|";
echo "=================================================";
echo " Version 0.4b  http://goo.gl/8mFHE5  @jjtibaquira";
echo " Email: jko@dragonjar.org  |   www.dragonjar.org";
echo "=================================================";
printf "\n"

ismacox=$(sw_vers 2>/dev/null)

#Check if is it root
if ! [ $(id -u) = 0 ] && ! [[ $ismacox ]] ; then
 echo "[-] You must be a root user" 2>&1
 exit 1
fi

nmapversion=$(which nmap 2>/dev/null)
paythonversion=$(which python 2>/dev/null)
pipversion=$(which pip 2>/dev/null)
md5sum=$(which md5sum 2>/dev/null)
md5=$(which md5 2>/dev/null)
kernel=$(uname -r)
os="$(uname -s) $kernel"
arch=$(uname -m)

function createConfigFile(){
  checksum=
  dbpath=$(find /usr -type f -name "script.db" 2>/dev/null | awk 'gsub("script.db","")')
  if [[ $dbpath ]]; then
    filePath=$dbpath'script.db'
    if [[ $ismacox ]]; then
      printf "[+] CheckSum MacSOX....\n"
      checksum=$(md5 $filePath | awk '{print $4}')
    else
      printf "[+] CheckSum not MacSOX....\n"
      checksum=$(md5sum $filePath | awk '{print $1}')
    fi
    printf "[+] Creating config.yaml file ...\n"
    printf "config: \n" > config.yaml
    printf "  scriptsPath: '$dbpath'\n" >> config.yaml
    printf "  filePath: '$filePath'\n" >> config.yaml
    printf "  fileBackup: 'scriptbk.db'\n" >> config.yaml
    printf "  scriptdb: 'nmap_scripts.sqlite3'\n" >> config.yaml
    printf '  categories: {"auth","broadcast","brute","default","discovery","dos","exploit","external","fuzzer","intrusive","malware","safe","version","vuln"}\n' >> config.yaml
    printf "  checksum: '$checksum'\n" >> config.yaml
    chmod 777 config.yaml
  fi
  printf "[+] NSEarch is ready for be launched uses python nsearch.py\n"
}

function installPipRequeriments(){
  printf "[+] Checking pip libs ...\n"
  pip install -r requirements.txt
}

function installpipDebian(){
  printf "[+] Installing pip ...\n"
  apt-get install python-pip -y
  installPipRequeriments
}

function installpipRedHat(){
  printf "[+] Installing pip ...\n"
  rpm -iUvh http://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm; yum -y update
  yum install python-pip -y
  installPipRequeriments
}

if [ -f /etc/lsb-release ] || [ -f /etc/debian_version ] ; then
  printf "[+] Checking Dependencies for $os ($arch $kernel)....\n"
  apt-get install unzip libreadline-gplv2-dev build-essential checkinstall unzip sqlite3 libsqlite3-dev -y

  if [[ $nmapversion ]]; then
    printf "\n[+] Nmap already installed :D \n"
  else
    echo "[+] Installing nmap .... "
    apt-get install nmap -y
  fi

  if [[ $paythonversion ]]; then
    printf "[+] Python is already installed :D\n"
    if [[ $pipversion ]]; then
      printf "[+] Pip is already installed :D\n"
      installPipRequeriments
    else
      installpipDebian
    fi
  else
    echo "Installing python ..."
    apt-get install python -y
    installpipDebian
  fi
  createConfigFile
elif [ -f /etc/redhat-release ]; then
  printf "[+] Checking Dependencies for $os ($arch $kernel)....\n"
  yum install zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel -y
  if [[ $nmapversion ]]; then
    printf "\n[+] Nmap already installed :D \n"
  else
    echo "[+] Installing nmap .... "
    yum install nmap -y
  fi

  if [[ $paythonversion ]]; then
    printf "[+] Python is already installed :D\n"
    if [[ $pipversion ]]; then
      printf "[+] Pip is already installed :D\n"
      installPipRequeriments
    else
      installpipRedHat
    fi
  else
    echo "Installing python ..."
    yum install python -y
    installpipRedHat
  fi
  createConfigFile
elif [[ $ismacox ]]; then
  printf "[+] Checking Dependencies for $os ($arch $kernel)....\n"
  brew install -v sqlite3
  if [[ $nmapversion ]]; then
    printf "\n[+] Nmap already installed :D \n"
  else
    echo "[+] Installing nmap .... "
    brew install -v nmap
  fi
  if [[ $paythonversion ]]; then
    printf "[+] Python is already installed :D\n"
    printf "[+] Pip is already installed :D\n"
    installPipRequeriments
  else
    echo "Installing python ..."
    brew install python -v
    printf "[+] Pip is already installed :D\n"
    installPipRequeriments
  fi
  createConfigFile
else
  if [[ $nmapversion ]] && [[ $paythonversion ]] && [[ $pipversion ]]; then
    printf "[+] Checking Dependencies for $os ($arch $kernel)....\n"
    installPipRequeriments
    printf "[+] Requirement already satisfied ... \n"
    createConfigFile
  else
    echo "[-] Could not find a autoinstall for $os ($arch $kernel)"
  fi
fi
