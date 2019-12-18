#!/bin/bash

progress_bar () {
    dpkg -s bc &> /dev/null  

    if [ $? -ne 0 ]; then

        if [ `whoami` != root ]; then
            echo "FAIL: You are not root."
            echo "Please run this script as root or using sudo"
            exit
        else
            echo "Script is missing an important dependancy. Installing this dependancy now."
            sleep 2 
        fi  

        local apt=`command -v apt-get`
        local yum=`command -v yum`

        if [ -n "$apt" ]; then
            apt-get update
            apt-get install -y bc

        elif [ -n "$yum" ]; then
            yum update 
            yum install -y bc
        else
            echo "Err: no path to apt-get or yum" >&2;
            exit 1;
        fi

        echo "Done! Please restart this script."
        exit 1;
    fi


    local waittime=$(echo "$1/50" | bc -l )

    for i in {1..50} ; do
        echo -n '['
        for ((j=0; j<i; j++)) ; do echo -n '='; done
        echo -n '=>'
        for ((j=i; j<50; j++)) ; do echo -n ' '; done
        if [ $i = 50 ]; then 
            echo -n "]" $'\n'
        else
            echo -n "]" $'\r'
        fi
        sleep $waittime
    done
}

echo -------------------- CHECKING ROOT STATUS --------------------
progress_bar 4

if [ `whoami` != root ]; then
    echo "FAIL: You are not root."
    echo "Please run this script as root or using sudo"
    exit
else
    echo "SUCCESS: You are root!"
fi


echo -e "\n"
echo -------------------- CONFIRMING INSTALLATION --------------------

while true; do
    echo "This script is intended to be run on a freshly installed Debian or CentOS based system."
    read -p "Do you wish to continue?" yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done


echo -e "\n"
echo -------------------- CHECKING PYTHON3 INSTALLATION --------------------
progress_bar 4
ret=`python3 -c 'import sys; print("True" if sys.version_info > (3, 6) else "False")'`

if [ ${ret} = "True" ]; then
    echo "SUCCESS: Python version 3.6+ already installed."
else 
    echo "FAIL: python version 3.6+ required. TIP: Python 3.7.3 comes as a standard package in Debian Buster based systems."
    exit 1;
fi


echo -e "\n"
echo -------------------- PREFORMING ANY SYSTEM UPDATES --------------------
echo you have to wait 5 seconds to proceed ...
echo or
echo hit Ctrl+C to quit
echo -e "\n"
progress_bar 6

package=$1
apt=`command -v apt-get`
yum=`command -v yum`

if [ -n "$apt" ]; then
    #this bit is just to make sure we can get all the software packages we need.
    #and remove arbitrary limitations imposed by debian developers
    apt-get update
    apt-get install software-properties-common

    apt-add-repository contrib
    apt-add-repository non-free

    apt-get update
    apt-get upgrade -y
    apt-get dist-upgrade -y

elif [ -n "$yum" ]; then
    yum update 
    yum upgrade -y
else
    echo "Err: no path to apt-get or yum" >&2;
    exit 1;
fi


echo -e "\n"
echo -------------------- INSTALLING REQUIRED PACKAGES --------------------
progress_bar 4
packages=(
    build-essential
    screen
    htop
    iftop
    python3-pip
    python-qrtools
    libzbar-dev
    libzbar0
    libgtk2.0-dev
    libv4l-dev
)

for p in "${packages[@]}"
do
    : 
    if [ -n "$apt" ]; then
        apt-get install -y $p

    elif [ -n "$yum" ]; then
        yum install -y $p
    else
        echo "Err: no path to apt-get or yum" >&2;
        exit 1;
    fi
   
done


echo -e "\n"
echo -------------------- INSTALLING REQUIRED PYTHON PACKAGES --------------------
progress_bar 4
packages=(
    aiohttp
    async-timeout
    yarl
    attrs
    multidict
    chardet
    idna
    discord.py[voice]
    asyncpg
    apscheduler
    sqlalchemy
    pillow
    qrcode[PIL]
    pypng 
    pyzbar
    pyzbar[scripts]
    psutil
    PYyaml
)

for p in "${packages[@]}"
do
    : 
    pip3 install ${p}
done


echo -e "\n"
echo -------------------- INSTALLING POSTGRESQL 11 --------------------
progress_bar 4

if [ -n "$apt" ]; then
    apt-get install -y postgresql-11

elif [ -n "$yum" ]; then
    yum install -y postgresql-11
else
    echo "Err: no path to apt-get or yum" >&2;
    exit 1;
fi


echo -e "\n"
echo -------------------- SETTING UP POSTGRESQL 11 --------------------
sleep 1

while true; do
    echo "INFO: By default; postgresql does not allow any remote connections, this is fine if you're running the bot and the database on the same box AND never wish to access the database on pgAdmin from another computer."
    echo "However, if this does not apply to you, PostgreSQL settings need to be changed."
    read -p "Would you like me to do this for you?" yn
    case $yn in

        [Yy]* ) 
            echo "Backing up postgresql.conf as postgresql.conf.bak"
            progress_bar 3
            cp /etc/postgresql/11/main/postgresql.conf /etc/postgresql/11/main/postgresql.conf.bak
            echo "Backing up pg_hba.conf as pg_hba.conf.bak"
            progress_bar 3
            cp /etc/postgresql/11/main/pg_hba.conf /etc/postgresql/11/main/pg_hba.conf.bak


            echo "Changing postgresql.conf and pg_hba.conf settings to allow remote connections from the same network."
            progress_bar 3
            sed -i "/# what IP address(es) to listen on;/ s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/11/main/postgresql.conf
            sed -i '/md5/ s/127.0.0.1\/32/samenet/g' /etc/postgresql/11/main/pg_hba.conf
            sed -i '/md5/ s/::1\/128/FE80::\/10/g' /etc/postgresql/11/main/pg_hba.conf

            break;;

        [Nn]* ) 
            echo "No settings changed."
            break;;

        * ) echo "Please answer yes or no.";;
    esac
done


echo -e "\n"
echo -------------------- STARTING POSTGRESQL 11 --------------------
progress_bar 4

systemctl restart postgresql


echo -------------------- CONFIGURING POSTGRESQL 11 --------------------
sleep 1

while true; do
    echo "The master login for postgresql is called 'postgres' however it requires a password to be set before you can log into the database with it."
    echo "I can set the default password on this account to 'postgres' for you to make logging in with pgadmin possible without running psql commands manually."
    echo "Once you're signed into pgadmin with the master 'postgres' login you can easily change this password to something else."
    read -p "Would you like to set the master password to 'postgres'?" yn
    case $yn in
        [Yy]* ) 
            su - postgres --session-command "psql -c \"alter user postgres with password 'postgres'\""
            break;;
        [Nn]* ) 
            break;;
        * ) echo "Please answer yes or no.";;
    esac
done


