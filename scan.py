from bluepy import btle
import logging
import os
import sys

import ConfigReader


def ScanForTomatoOrDie():

    if os.geteuid() !=0:
        print ('you need root permission for ble scanning.')
        print ('please run the program with sudo ...')
        print ('program exiting.')
        sys.exit(0)
    
    logging.info('scaning for tomato...')
    scanner = btle.Scanner()
    print('scanning for miaomiao devices')
    devices = scanner.scan(7)
    
    found_devices = 0
    tomato_device = None
    print('devices found:')
    for device in devices:
        name = device.getValueText(9)
        print (device.addr,  device.addrType, name)
        if 'miaomiao' in name:
            found_devices +=1
            tomato_device = device
    
    if found_devices == 0:
        print('No miaomiao devices found, please try again. Program exiting.')
        sys.exit(0)
        
    if found_devices > 1:
        print ('More then one device found, Program exiting.')
        sys.exit(0)
    
    print('Will use device ', device.getValueText(9), device.addr)
    ConfigReader.g_config.UpdateSection('BTDevice', 'bt_mac_address', device.addr)  
        
         
if __name__ == "__main__":
    ScanForTomatoOrDie()