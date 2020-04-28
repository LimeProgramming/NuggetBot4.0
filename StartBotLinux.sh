#!/bin/bash

runbot=1
reboot=0


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


while [ $runbot -gt 0 ]

do
    python3.7 runbot.py

    while IFS= read -r line
    do
        if [ "$line" -eq "1" ]; then
            reboot=1
        else
            runbot=0
        fi
    done < data/reboot.txt

    if [ "$reboot" -eq 1 ]; then
        echo -------------------- REBOOTING BOT --------------------
        progress_bar 6
        reboot=0
        echo 0 > data/reboot.txt
    fi

done




