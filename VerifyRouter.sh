SLEEP_TIME=60
sleep $SLEEP_TIME
DEFAULT_GATEWAY=`route -n | grep ^0.0.0.0 | grep wlan0 |awk '{print $2 }'`
echo $DEFAULT_GATEWAY

while true
do
    if [ "$DEFAULT_GATEWAY" = "0.0.0.0" ]; then
         echo "fail because of 0.0.0.0"
         COUNT=$((COUNT+1))
    else
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
    # Get the default gateway again
    DEFAULT_GATEWAY=`route -n | grep ^0.0.0.0 | grep wlan0 |awk '{print $2 }'`
    echo $DEFAULT_GATEWAY

done


