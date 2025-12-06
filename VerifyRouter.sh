SLEEP_TIME=60
sleep $SLEEP_TIME
DEFAULT_GATEWAY=`route -n | grep ^0.0.0.0 | grep wlan0 |awk '{print $2 }'`
echo $DEFAULT_GATEWAY

echo Starting script

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

    iwconfig
    my_ap=$(iwconfig wlan0 | grep Access)
    my_date=$(date +"%F %T")
    echo xxxx $my_date $my_ap
    echo counter is now $COUNT
    #Check the values
    if [[ $COUNT -gt 10 ]]
    then
       echo rebooting
       sudo reboot
    fi
    sleep $SLEEP_TIME

done


