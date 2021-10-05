# Configuring Raspberry Pi for Libre 2

## Table of Contents
  - [Step 0 - Install the Pi with the latest Raspberry Pi OS](#step-0---install-the-pi-with-the-latest-raspberry-pi-os)
  - [Step 1 - (Good practices, optional):](#step-1---good-practices-optional)
  - [Step 2 - Connect the pi to wifi.](#step-2---connect-the-pi-to-wifi)
  - [Step 3 - Install the required packages](#step-3---install-the-required-packages)
  - [Step 4 - Run the program:](#step-4-run-the-program)
  - [Step 5 - Configure xDrip to connect to PI](#step-5-configure-xdrip-to-connect-to-pi)
  - [Step 6 - Configure Pi to connect to xdrip](#step-6---configure-pi-to-connect-to-xdrip)
  - [Step 7 - Configure the pi to also upload data to a mongodb (optional).](#step-7---configure-the-pi-to-also-upload-data-to-a-mongodb-optional)
  - [Step 7 - Configure a phone as receiver (optional)](#step-7---configure-a-phone-as-receiver-optional)
  - [Appendix A - Important screen commands (just information nothing to do):](#appendix-a---important-screen-commands-just-information-nothing-to-do)
  - [Appendix B - Configuring the pis to be detected by xDrip.](#appendix-b---configuring-the-pis-to-be-detected-by-xdrip)
  - [Appendix C - Copying private key to raspberry pis. (optional)](#appendix-c---copying-private-key-to-raspberry-pis-optional)
  - [Appendix D - Configuring raspberry-pi from command line.](#appendix-d---configuring-raspberry-pi-from-command-line)

## Step 0 - Install the Pi with the latest Raspberry Pi OS
https://www.raspberrypi.org/software/operating-systems/

Lite version works fine but will need to enable SSH to access the terminal remotely

## Step 1 - (Good practices, optional):

Go to preferences -> raspberry pi configuration:

Configure password, hostname,

On interfaces, allow ssh.

Localization, fix locale, timezone, keyboard, wifi country.

Reboot when needed.

## Step 2 - Connect the pi to wifi.

For Lite OS you need to do this when flashing the SD card. It is no longer necessary to edit the config files manually - using Raspberry Pi Imager, you can press Ctrl+Shift+X to bring up the advanced options which allow you to configure wifi, hostname, locale and enable SSH from a GUI.

Once connected to wifi, remember the IP address that you are assigned as this will be needed for step 5.

## Step 3 - Install the required packages
Open terminal on rpi

    sudo apt-get install -y screen
    sudo apt-get install -y python3-pip libglib2.0-dev
    sudo pip3 install bluepy
    sudo pip3 install pymongo
    sudo pip3 install dnspython
    sudo apt-get install -y vim

## Step 4 - Run the program:

If you do not have git installed, you will need to install that too:

    sudo apt-get install -y git

To run the program manually do: 

1. git clone https://github.com/tzachi-dar/LibreAllHouse.git
2. cd LibreAllHouse/
3. Edit the config.cfg file to unter mongodb parameters (optional). (for example db_uri = mongodb+srv://userj:passi@cluster-b6k1n0tj.bg18m.mongodb.net/heroku_b6k1n0tj)
4. sudo python3 main.py 

In order to run the program automatically after boot edit the file `/etc/rc.local`:
    
    sudo pico /etc/rc.local

And add the line (before the exit 0 line):

    /usr/bin/screen -L -Logfile /home/pi/LibreAllHouse/screen.log -dmS tomato python3 /home/pi/LibreAllHouse/main.py

Reboot the pi and look at the file /home/pi/LibreAllHouse/screen.log to see if things are working as expected.

To look at the file use:

    tail -F ~/LibreAllHouse/screen.log  

Ctrl+C to cancel monitoring log 
 
## Step 5 - Configure xDrip to connect to PI

1.  On Hardware Data Source select ‘Libre wifi’ or ‘Libre Bluetooth + wifi’
    
2.  On the list of receivers, enter the list of raspberry pis and/or the mongodb addresses. The raspberry pi software runs on port 50005 so you need to include this in the address For example:

`192.168.1.2:50005,mongodb://user:[pass@ds11551.mlab.com](mailto:pass@ds11551.mlab.com):11551/nightscout3/libre`

Replace nightscout3 with your connection.

## Step 6 - Configure Pi to connect to xdrip
1. On the pi, inside the LibreAllHouse directory, open the config.cfg file

	`sudo pico config.cfg`

2. Change the **api_secret** property to be anything you like (remember this secret)
3. Save the config file
4. In xdrip, go to `Settings -> Inter-app settings`.
5. Enable **xDrip Web Service**
6. Check the box for **Open Web Service**
7. Enter an **xDrip Web Service Secret**. This should match the secret configured in the **config.cfg** file on your Pi

## Step 7 - Configure the pi to also upload data to a mongodb (optional).

This is an optional step, and is only needed if your pis are not connected to the same network as xdrip.

Most people will not need to use it.

On the config.cfg file you need to set the parameters of the mongodb. For example:

If you are connecting to atlasdb it should look like:

[MongoData]

db_uri = mongodb+srv://USER:PASSWORD@URLPREFIX.mongodb.net

db_name = DBNAME

collection_name = COLLECTION

## Step 8 - Configure a phone as receiver (optional)

### It is also possible to use a phone with xdrip to upload the data to the mongo db:

1. on the watch, go to settings->cloud upload->mongo db
	a) enable nightscout mongodb sync.
	b) enter the mongodb uri
	c) enable **upload libre transmitter data**

You can now see that data received by this watch is uploaded to the mongo db to a collection called libre.

## Appendix A - Important screen commands (just information nothing to do):

Since program runs in screen, here are some screen commands for debugging.

To show existing screen sessions:

    Screen -ls

Attach a screen session:

    Screen -r [session name]

Temporarily leave screen session: **CTRL-A CTRL-D**

Kill a screen session: **Ctrl+D**

Tail

## Appendix B - Configuring the pis to be detected by xDrip.

Should work by default on recent raspberry pis.

If you want to be able to ping a pi using a windows machine you will have to setup an mdns client. For example from here: [https://support.apple.com/kb/DL999?locale=en_US](https://support.apple.com/kb/DL999?locale=en_US)
  

## Appendix C - Copying private key to raspberry pis. (optional)

Full explanation can be found at: [https://dvpizone.wordpress.com/2014/03/02/how-to-connect-to-your-raspberry-pi-using-ssh-key-pairs/](https://dvpizone.wordpress.com/2014/03/02/how-to-connect-to-your-raspberry-pi-using-ssh-key-pairs/) 

Here is a very short explanation.

The file .ssh/authorized_keys should have a line that was created with puttygen

The public key after saves looks like:

    ---- BEGIN SSH2 PUBLIC KEY ----
    Comment: "rsa-key-20180419"
    AAAAB3NzaC1yc2EAAAABJQAAAQEA3uY4G+v8jIRRUgp4cc0b4HwedH4hOmfFvCPc
    2MtctoqZ+fBk23YIp0LPEOMhtj2DS9Qypf5SXkoTWBdj2lQXOVdxTXjqVTbsZwDH
    vMz+IShVgCAxAyQXMJFE+IkVA4C0Qn68Tn1dLj7GAkrn4zJE3revI6jHr5iJCnDA
    yKDjRKRlTBkSr+9DG6N1bgFamhC1CDnE/fmXTEe+16GvcgYSOSmCK1fPrJ5oSQkc
    bDNNOPEYuuA9CmSXQKLlU5w+szFbO5AvFtXnS+fXAc8HSyWqF7D5hFzIgS2qCbdS
    6yWkFQMy79YAguHed98ihju98yCNGvmqAIOxb2AETmDv1fcfQw==
    ---- END SSH2 PUBLIC KEY ----

 You need to copy only:

    ssh-rsa
    AAAAB3NzaC1yc2EAAAABJQAAAQEA3uY4G+v8jIRRUgp4cc0b4HwedH4hOmfFvCPc
    2MtctoqZ+fBk23YIp0LPEOMhtj2DS9Qypf5SXkoTWBdj2lQXOVdxTXjqVTbsZwDH
    vMz+IShVgCAxAyQXMJFE+IkVA4C0Qn68Tn1dLj7GAkrn4zJE3revI6jHr5iJCnDA
    yKDjRKRlTBkSr+9DG6N1bgFamhC1CDnE/fmXTEe+16GvcgYSOSmCK1fPrJ5oSQkc
    bDNNOPEYuuA9CmSXQKLlU5w+szFbO5AvFtXnS+fXAc8HSyWqF7D5hFzIgS2qCbdS
    6yWkFQMy79YAguHed98ihju98yCNGvmqAIOxb2AETmDv1fcfQw==

 In other words remove 3 lines, and add **ssh-rsa** in the beginning.

## Appendix D - Configuring raspberry-pi from command line.

Host name: [https://www.howtogeek.com/167195/how-to-change-your-raspberry-pi-or-other-linux-devices-hostname/](https://www.howtogeek.com/167195/how-to-change-your-raspberry-pi-or-other-linux-devices-hostname/)

Timezone: dpkg-reconfigure tzdata

