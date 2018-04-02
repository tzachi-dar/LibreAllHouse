from bluepy import btle
import time  
import binascii
import struct
from time import gmtime, strftime
import datetime
import sys
import socket
from pymongo import MongoClient
import sqlite3
import os
import inspect
import threading
import json
import signal
import bson


'''------------------------------- TODO -----------------------------------'''
# Read config from file.
# Use standard methods for log.
# Split to files.
# Init flow.


''' ------------------------ Config data ----------------------------------'''

# Read from a config file.
db_uri = 'mongodb://user:pass@ds115166.mlab.com:15166'
db_name = 'nightscout3'
collection_name = 'libre'

''' ------------------------ sqllite3 functions ---------------------------'''

class sqllite3_wrapper:

    path = os.path.dirname(os.path.abspath(inspect.stack()[0][1]))
    file_name = path+os.sep+'LibreReadings.db'

    def CreateTable(self):
        print(self.file_name)
        conn = sqlite3.connect(self.file_name)
        cursor=conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS LibreReadings (
                                    BlockBytes BLOB NOT NULL,
                                    CaptureDateTime BIGINT,
                                    ChecksumOk int,
                                    DebugInfo text NOT NULL,
                                    TomatoBatteryLife integer,
                                    UploaderBatteryLife integer,
                                    Uploaded int,
                                    HwVersion int,
                                    FwVersion int,
                                    SensorId text,
                                    PRIMARY KEY (CaptureDateTime, DebugInfo))''')
        conn.commit()
        conn.close()

    def InsertReading(self, BlockBytes, CaptureDateTime, ChecksumOk, DebugInfo, TomatoBatteryLife = 50, UploaderBatteryLife = 100,
                      Uploaded = 0, HwVersion = 1, FwVersion = 0, SensorId = "" ):
        #expects a dict like the one created in create_object
        conn = sqlite3.connect(self.file_name)
        with conn:
            cursor=conn.cursor()
            cursor.execute("INSERT INTO LibreReadings  values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sqlite3.Binary(BlockBytes), 
                 CaptureDateTime,
                 ChecksumOk,
                 DebugInfo,
                 TomatoBatteryLife,
                 UploaderBatteryLife,
                 Uploaded,
                 HwVersion,
                 FwVersion,
                 SensorId))
             

    def GetLatestObjects(self, count, only_not_uploaded):
        # gets the latest n non commited objects
        ret = []
        conn = sqlite3.connect(self.file_name)
        with conn:
            if only_not_uploaded:
                cursor = conn.execute("SELECT * FROM LibreReadings WHERE Uploaded=:Uploaded ORDER BY CaptureDateTime DESC LIMIT :Limit", 
                    {"Uploaded": 0, "Limit": count})
            else:
                cursor = conn.execute("SELECT * FROM LibreReadings ORDER BY CaptureDateTime DESC LIMIT :Limit", 
                    {"Limit": count})
        
            for raw in cursor:
                raw_dict = dict()
                #print(type(raw[0])) 
                raw_dict['BlockBytes'] = bson.binary.Binary(bytes(raw[0]))
                raw_dict['CaptureDateTime'] = raw[1]
                raw_dict['ChecksumOk'] = raw[2]
                raw_dict['DebugInfo'] = raw[3]
                raw_dict['TomatoBatteryLife'] = raw[4]
                raw_dict['UploaderBatteryLife'] = raw[5]
                raw_dict['Uploaded'] = raw[6]
                raw_dict['HwVersion'] = raw[7]
                raw_dict['FwVersion'] = raw[8]
                raw_dict['SensorId'] = raw[9]
                # reverse the list to get is ASC but from the end.
                ret.insert(0,raw_dict)
        for raw in ret:
            print(raw)
        return ret
    
    def UpdateUploaded(self, CaptureDateTime, DebugInfo):
        conn = sqlite3.connect(self.file_name)
        with conn:
            cur = conn.cursor()    
            cur.execute("UPDATE LibreReadings SET Uploaded=? WHERE CaptureDateTime=? and DebugInfo=?", (1, CaptureDateTime, DebugInfo))        
            conn.commit()
            print ("Number of rows updated: %d" % cur.rowcount)

    def RunLocalTests(self):
        sqw = sqllite3_wrapper ()
        sqw.CreateTable()
        for i in range(1, 3):
            if not i % 1000: print(i)
            #obj = create_object('port1', '6FNTM 54880 44800 213 -89 2')
            sqw.InsertReading('bb', 1000 + i, 1, 'debug', 50)

        print("before get")
        lastones = sqw.GetLatestObjects(5, False)
        for ob in lastones:
            sqw.UpdateUploaded(ob['CaptureDateTime'], ob['DebugInfo'])
        sys.exit(0)

sqw = sqllite3_wrapper ()
sqw.CreateTable()
#sqw.RunLocalTests()


''' ------------------------- MongoWrapper class ----------------------------------'''

def log(file, string):
    i = datetime.datetime.now()
    now = "%s" %i 
    print (now[:-3]+ ':  ' +string)
    file.write(now[:-3]+ ':  ' + string)
    file.write('\r\n')


class MongoWrapper(threading.Thread):

    event = None
    log_file = None
    

    def __init__(self, log_file):
        self.event = threading.Event()
        self.log_file =log_file
        threading.Thread.__init__(self)

    def SetEvent(self):
        self.event.set()

    def run(self):
        #This threads loop and reads data from the sql, and uploads it to the mongo DB.
        #It starts to work based on the event or based on 1 minutes timeout.
        log(log_file, "Starting mongo thread")
        while True:
            try:
                ret = self.event.wait(1*60)
                log(log_file, "event wait ended, ret = %s" % ret)
                # The next line introduces many races that are only fixed by the timeout on wait.
                self.event.clear()
                sqw = sqllite3_wrapper ()
                not_uploaded_readings = sqw.GetLatestObjects(12 * 8, True)
                for reading_dict in not_uploaded_readings:
                    MongoWrapper.write_object_to_mongo(log_file, reading_dict)
                    sqw.UpdateUploaded(reading_dict['CaptureDateTime'], reading_dict['DebugInfo'])
            except Exception as exception :  
               log(log_file, 'caught exception in MongoThread, will soon continue' + str(exception) + exception.__class__.__name__)
               time.sleep(60)
    @staticmethod
    def write_log_to_mongo(log_file, device_name, log_message):
        mongo = dict()
        captured_time = int(time.time() * 1000)
        mongo['CaptureDateTime'] = captured_time
        mongo['DebugMessage'] = '%s %s %s %s' % (socket.gethostname(), time.strftime('%d-%m-%Y %H:%M:%S', time.localtime(captured_time / 1000)) , device_name, log_message)
        MongoWrapper.write_object_to_mongo(log_file, mongo)
        log(log_file, "sent %s to mongo" % log_message)
   
    @staticmethod
    def write_object_to_mongo(log_file, mongo_dict):
        client = MongoClient(db_uri+ '/'+db_name + '?socketTimeoutMS=180000&connectTimeoutMS=60000')
        db = client[db_name]
        collection = db[collection_name]
        insertion_result = collection.insert_one(mongo_dict)
        log(log_file, "succesfully uploaded object to mongo insertion_result = %s" % insertion_result.acknowledged)

log_file = open('log_hist.txt' , 'a', 1)

# sleep for 30 seconds to let the system connect to the network
# ???? time.sleep(30)

#Create the sqllite table. (done above currently).
#sqw = sqllite3_wrapper ()
#sqw.CreateTable()


try:
    MongoWrapper.write_log_to_mongo(log_file, 'device_name', "starting program")
except Exception as exception :  
    log(log_file, 'caught exception in first write ' + str(exception) + exception.__class__.__name__)

try:
    mongo_wrapper = MongoWrapper(log_file)
    mongo_wrapper.start()
except Exception as exception :  
    # This is a critical failure, we will continue going up, but in a very bad state. Consider quiting the program
    log(log_file, 'WTF, caught exception in MongoWrapper cration ' + str(exception) + exception.__class__.__name__)               
               

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
        
        captured_time = int(time.time() * 1000)
        DebugInfo = '%s %s %s' % (socket.gethostname(), time.strftime('%d-%m-%Y %H:%M:%S', time.localtime(captured_time / 1000)), 'tomato')
        
        sqw = sqllite3_wrapper( )
        sqw.InsertReading(real_data, captured_time, checksom_ok, DebugInfo)
        mongo_wrapper.SetEvent()


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
        cheksum_ok1 = self.CheckCRC16(data, 0 ,24)
        print('cheksum_ok1 = ', cheksum_ok1)
        cheksum_ok2 = self.CheckCRC16(data, 24 ,296)
        print('cheksum_ok2 = ', cheksum_ok2)
        cheksum_ok3 = self.CheckCRC16(data, 320 ,24)
        print('cheksum_ok3 = ', cheksum_ok3)
        return cheksum_ok1 & cheksum_ok2 & cheksum_ok3

 
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
