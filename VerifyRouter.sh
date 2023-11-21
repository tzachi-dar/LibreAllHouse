SLEEP_TIME=60
sleep $SLEEP_TIME
DEFAULT_GATEWAY=`route -n | grep ^0.0.0.0 | grep wlan0 |awk '{print $2 }'`
echo $DEFAULT_GATEWAY

while true
do
    ping -c 1 $DEFAULT_GATEWAY
    RET=$?
    if [[ $RET -eq 0 ]]
    then
       echo "successes"
       COUNT=0
    else
       echo fail
       COUNT=$((COUNT+1))
    fi

    date
    echo counter is now $COUNT
    #Check the values
    if [[ $COUNT -gt 10 ]]
    then
       echo rebooting
       sudo reboot
    fi
    sleep $SLEEP_TIME

done


