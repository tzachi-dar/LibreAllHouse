from bluepy import btle
import time  
import binascii
import struct
from time import gmtime, strftime


class DataCollector():
    def __init__(self):
        self.data_ =  ''
        self.recviedEnoughData = False
        self.lastReceiveTimestamp_ = time.time()
        
        
        self.crc16table = [
        0, 4489, 8978, 12955, 17956, 22445, 25910, 29887, 35912,
        40385, 44890, 48851, 51820, 56293, 59774, 63735, 4225, 264,
        13203, 8730, 22181, 18220, 30135, 25662, 40137, 36160, 49115,
        44626, 56045, 52068, 63999, 59510, 8450, 12427, 528, 5017,
        26406, 30383, 17460, 21949, 44362, 48323, 36440, 40913, 60270,
        64231, 51324, 55797, 12675, 8202, 4753, 792, 30631, 26158,
        21685, 17724, 48587, 44098, 40665, 36688, 64495, 60006, 55549,
        51572, 16900, 21389, 24854, 28831, 1056, 5545, 10034, 14011,
        52812, 57285, 60766, 64727, 34920, 39393, 43898, 47859, 21125,
        17164, 29079, 24606, 5281, 1320, 14259, 9786, 57037, 53060,
        64991, 60502, 39145, 35168, 48123, 43634, 25350, 29327, 16404,
        20893, 9506, 13483, 1584, 6073, 61262, 65223, 52316, 56789,
        43370, 47331, 35448, 39921, 29575, 25102, 20629, 16668, 13731,
         9258, 5809, 1848, 65487, 60998, 56541, 52564, 47595, 43106,
        39673, 35696, 33800, 38273, 42778, 46739, 49708, 54181, 57662,
        61623, 2112, 6601, 11090, 15067, 20068, 24557, 28022, 31999,
        38025, 34048, 47003, 42514, 53933, 49956, 61887, 57398, 6337,
         2376, 15315, 10842, 24293, 20332, 32247, 27774, 42250, 46211,
        34328, 38801, 58158, 62119, 49212, 53685, 10562, 14539, 2640,
         7129, 28518, 32495, 19572, 24061, 46475, 41986, 38553, 34576,
        62383, 57894, 53437, 49460, 14787, 10314, 6865, 2904, 32743,
        28270, 23797, 19836, 50700, 55173, 58654, 62615, 32808, 37281,
        41786, 45747, 19012, 23501, 26966, 30943, 3168, 7657, 12146,
        16123, 54925, 50948, 62879, 58390, 37033, 33056, 46011, 41522,
        23237, 19276, 31191, 26718, 7393, 3432, 16371, 11898, 59150,
        63111, 50204, 54677, 41258, 45219, 33336, 37809, 27462, 31439,
        18516, 23005, 11618, 15595, 3696, 8185, 63375, 58886, 54429,
        50452, 45483, 40994, 37561, 33584, 31687, 27214, 22741, 18780,
        15843, 11370, 7921, 3960 ]
        
    def reinit(self):
        self.data_ =  ''
        self.recviedEnoughData = False
        
        
    def AcumulateData(self, new_data):
        if time.time() - self.lastReceiveTimestamp_ > 20:
            # Too much time from last time
            print('restrarting since time from last packet is ', (time.time() - self.lastReceiveTimestamp_), ' already acumulated ', len(self.data_))
            self.reinit()
            
        self.lastReceiveTimestamp_ = time.time()
    
        self.data_ = self.data_ + new_data
        #print('total = ' ,binascii.b2a_hex(self.data_))
        self.AreWeDone()
        
    def AreWeDone(self):
        if self.recviedEnoughData:
            return
        if len(self.data_) < 344 + 18 + 1:
            return
        self.recviedEnoughData = True
        print('we have enough data len = ', len(self.data_))
        real_data = bytearray(self.data_[18:344+18])
        #print('real_data = ', binascii.b2a_hex(real_data))
        checksom_ok = self.VerifyChecksum(real_data)
        print('checksum_ok = ', checksom_ok)


    
    
    # first two bytes = crc16 included in data
    def computeCRC16(self, data, start, size):
        crc = 0xffff;
        for i in range (start + 2, start + size):
            crc = ((crc >> 8) ^ self.crc16table[(crc ^ data[i]) & 0xff]);
      
        reverseCrc = 0;
        for i in range (0,16):
            reverseCrc = (reverseCrc << 1) | (crc & 1)
            crc >>= 1
        return reverseCrc

    def CheckCRC16(self, data, start, size):
        crc = self.computeCRC16(data, start, size)
        if crc == (data[start+1] * 256 + data[start]) : 
            return True
        return False

        
    def VerifyChecksum(self, data):
        #????????? FIX THIS
        cheksum_ok = self.CheckCRC16(data, 0 ,24)
        print('cheksum_ok1 = ', cheksum_ok)
        cheksum_ok = self.CheckCRC16(data, 24 ,296)
        print('cheksum_ok2 = ', cheksum_ok)
        cheksum_ok = self.CheckCRC16(data, 320 ,24)
        print('cheksum_ok3 = ', cheksum_ok)

 
data_collector = DataCollector() 
        
        

class MyDelegate(btle.DefaultDelegate):
    def __init__(self, params):
        btle.DefaultDelegate.__init__(self)
        print('Init called.')
        # ... initialise here
        self.count = 0

    def handleNotification(self, cHandle, data):
        # ... perhaps check cHandle
        # ... process 'data'
        #print ('notifcation calledi count = ', self.count , strftime("%Y-%m-%d %H:%M:%S", gmtime()),binascii.b2a_hex(data))
        data_collector.AcumulateData(data)
        #print(type(data))
        self.count +=1
        if self.count % 10 == 0:
            print (self.count)



def foo():     
    print ("Connecting...")
    dev = btle.Peripheral("DB:23:F4:F2:86:62", 'random')
    dev.setDelegate( MyDelegate('paramsi') )
     
    print ("Services...")
    for svc in dev.services:
        print (str(svc))
    
    NRF_UART_SERVICE = btle.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E") # nrfDataService
 
    print ("charterstics...")
    nrfGattService = dev.getServiceByUUID(NRF_UART_SERVICE)
    for ch in nrfGattService.getCharacteristics():
         print (str(ch))

    NRF_UART_RX = btle.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
    NRF_UART_TX = btle.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
    CLIENT_CHARACTERISTIC_CONFIG =  btle.UUID("00002902-0000-1000-8000-00805f9b34fb")
    
    nrfGattCharacteristic = nrfGattService.getCharacteristics(NRF_UART_TX)
    print ("nrfGattCharacteristic = ", nrfGattCharacteristic)
    #print  nrfGattCharacteristic.supportsRead()
    print (nrfGattCharacteristic[0].propertiesToString())
    #???nrfGattCharacteristic[0].write(struct.pack('<bb', 0x01, 0x00), False)
    bdescriptor =  nrfGattCharacteristic[0].getDescriptors(CLIENT_CHARACTERISTIC_CONFIG)
    bdescriptor[0].write(struct.pack('<bb', 0x01, 0x00), False)
    mCharacteristicSend = nrfGattService.getCharacteristics(NRF_UART_RX)[0]

    #charaProp = nrfGattCharacteristic.

    #str1 = "".join(map(chr, [209, 1]))
    #print(str1)
    #mCharacteristicSend.write(str1)
    
    str1 = "".join(map(chr, [240]))
    print(str1)
    mCharacteristicSend.write(str1)
       
    time.sleep(1.0) # Allow sensor to stabilize


    #lightSensorValue = lightService.getCharacteristics(NRF_UART_RX)[0]
    # Read the sensor
    
    while True:
        #val = lightSensorValue.read()
        #print ("Light sensor raw value", binascii.b2a_hex(val), val)
        dev.waitForNotifications(1.0)

foo()
