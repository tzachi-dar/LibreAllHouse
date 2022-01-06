#!/bin/bash
while true
do
	echo "Running program" $(date)  >> /home/pi/LibreAllHouse/screen.log 
        python3 /home/pi/LibreAllHouse/main.py >> /home/pi/LibreAllHouse/screen.log 2>&1
        echo "\nprogram death detected" $(date)  >> /home/pi/LibreAllHouse/screen.log
	sleep 60
done
