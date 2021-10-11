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
#import bson
import base64
import traceback
import logging
import random
import scan
from datetime import timedelta

import ConfigReader
import requests
import hashlib

'''------------------------------- TODO -----------------------------------'''
# Read configuration from file. [done]
# Use standard methods for log.
# Split code to files.
# Initialization flow.
# Don't send/upload data with filed checksum [done]
# Move to python 3. [done]
# Use strong types.
# more fields battery, fw, hw [done]
# retry after crc errors [done]
# Read every 5 minutes.
# Allow to replace sensors. [done]
# Always catch ctrl c. [done]


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
                                    HwVersion text,
                                    FwVersion text,
                                    SensorId text,
                                    PRIMARY KEY (CaptureDateTime, DebugInfo))''')
        
        if not self.DoesFieldExistInTable(cursor, 'NoSensor'):
            cursor.execute("alter table LibreReadings add column NoSensor integer" )
        
        conn.commit()
        conn.close()

    def InsertReading(self, BlockBytes, CaptureDateTime, ChecksumOk, DebugInfo, TomatoBatteryLife = 50, UploaderBatteryLife = 100,
                      Uploaded = 0, HwVersion = 0, FwVersion = 0, SensorId = "", NoSensor = False ):
        #expects a dict like the one created in create_object
        conn = sqlite3.connect(self.file_name)
        with conn:
            cursor=conn.cursor()
            cursor.execute("INSERT INTO LibreReadings  values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sqlite3.Binary(BlockBytes), 
                 CaptureDateTime,
                 ChecksumOk,
                 DebugInfo,
                 TomatoBatteryLife,
                 UploaderBatteryLife,
                 Uploaded,
                 HwVersion,
                 FwVersion,
                 SensorId,
                 NoSensor))
             

    def GetLatestObjects(self, count, only_not_uploaded, only_checksum_ok = False):
        # gets the latest n non commited objects
        
        uploaded_max = 0 if only_not_uploaded else 2
        checksum_min = 0 if only_checksum_ok else -1
        ret = []
        conn = sqlite3.connect(self.file_name)
        with conn:
            cursor = conn.execute("SELECT * FROM LibreReadings WHERE Uploaded<=:Uploaded AND ChecksumOk>:ChecksumOk ORDER BY CaptureDateTime DESC LIMIT :Limit", 
                    {"Uploaded": uploaded_max, "ChecksumOk": checksum_min, "Limit": count})
            
            for raw in cursor:
                raw_dict = dict()
                #print(type(raw[0])) 
                #raw_dict['BlockBytes'] = bson.binary.Binary(bytes(raw[0]))
                raw_dict['BlockBytes'] = base64.b64encode(raw[0]).decode('ascii')
                raw_dict['CaptureDateTime'] = raw[1]
                raw_dict['ChecksumOk'] = raw[2]
                raw_dict['DebugInfo'] = raw[3]
                raw_dict['TomatoBatteryLife'] = raw[4]
                raw_dict['UploaderBatteryLife'] = raw[5]
                raw_dict['Uploaded'] = raw[6]
                raw_dict['HwVersion'] = raw[7]
                raw_dict['FwVersion'] = raw[8]
                raw_dict['SensorId'] = raw[9]
                raw_dict['NoSensor'] = raw[10]
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

    def DoesFieldExistInTable(slef, cursor, field):
        cursor.execute('PRAGMA table_info(LibreReadings)')
        data = cursor.fetchall()
        for d in data:
            #print (d[0], d[1], d[2])
            if field == d[1]:
                return True
        return False
        
    def RunLocalTests(self):
        sqw = sqllite3_wrapper ()
        sqw.CreateTable()
        for i in range(0, 5):
            if not i % 1000: print(i)
            #obj = create_object('port1', '6FNTM 54880 44800 213 -89 2')
            sqw.InsertReading(b'bb', 1000 + i, i % 2, 'debug', 50, Uploaded = i%2)

        print("before get")
        lastones = sqw.GetLatestObjects(5, False)
        print("after get")
        for ob in lastones:
            print(ob)
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
        if not ConfigReader.g_config.db_uri:
             print('no config for mongo. Exiting')
             return
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
    def write_log_to_mongo(log_file, log_message):
        mongo = dict()
        captured_time = int(time.time() * 1000)
        mongo['CaptureDateTime'] = captured_time
        mongo['DebugMessage'] = '%s %s %s' % (socket.gethostname(), time.strftime('%d-%m-%Y %H:%M:%S', time.localtime(captured_time / 1000)) , log_message)
        MongoWrapper.write_object_to_mongo(log_file, mongo)
        log(log_file, "sent %s to mongo" % log_message)
   
    @staticmethod
    def write_object_to_mongo(log_file, mongo_dict):
        if not ConfigReader.g_config.db_uri:
            return 
        client = MongoClient(ConfigReader.g_config.db_uri + '?retryWrites=true&w=majority')
        db = client[ConfigReader.g_config.db_name]
        collection = db[ConfigReader.g_config.collection_name]
        insertion_result = collection.insert_one(mongo_dict)
        log(log_file, "successfully uploaded object to mongo insertion_result = %s" % insertion_result.acknowledged)
        client.close()


log_file = open('log_hist.txt' , 'a', 1)

# sleep for 30 seconds to let the system connect to the network (only at start of work)
# ???? time.sleep(30)

#Create the sqllite table. (done above currently).
#sqw = sqllite3_wrapper ()
#sqw.CreateTable()


''' ----------------- threads that respond to tcp requests -----------------------'''

def CreateVersion1Response(numberOfRecords, connlocal):
    ''' This code is here mainly to support a connection from old xDrip clients on g4'''
    reply = ''
    sqw = sqllite3_wrapper()
    readings = sqw.GetLatestObjects( numberOfRecords,False)
    for reading_dict in reversed(readings):
        reading_dict['RelativeTime'] = (int(time.time()*1000) ) - reading_dict['CaptureDateTime']
        if reading_dict['RelativeTime'] < 0:
            continue
        reply = reply + json.dumps(reading_dict) +"\n"

    return reply

def CreateVersion2Response(decoded, connlocal):
    ''' This code is to sens answers for the main libre protocol
    The answer should be a json object that contains general fields, and an array
    of json objects which are the real readings.

    
    {
        "debug_message":"aa",
        "last_reading":5,
        "libre_wifi_data":[{"CaptureDateTime":5,"ChecksumOk":0...},{"ChecksumOk":0,"FwVersion":0...}],
        "reply_version":2
    }

    '''

    reply = '{\n'
    reply += '"reply_version":2,\n'
    reply += '"max_protocol_version":2,\n'
    reply += '"device_type":"tomato",\n'
    
    reply += '"libre_wifi_data":['
    
    sqw = sqllite3_wrapper()
    readings = sqw.GetLatestObjects( decoded['numberOfRecords'],False)
    first = True
    for reading_dict in reversed(readings):
        if first == False:
            reply = reply + ",\n"
        first = False
        reading_dict['RelativeTime'] = (int(time.time()*1000) ) - reading_dict['CaptureDateTime']
        if reading_dict['RelativeTime'] < 0:
            continue
        reply = reply + json.dumps(reading_dict)
    reply += ']'
    reply += '}\n'
    return reply
    
   

def clientThread(connlocal):
    try:
        connlocal.settimeout(10)
        while True:
            data = connlocal.recv(1024)
            reply = ''
            if not data:
                break
            decoded = json.loads(data.decode('ascii'))
            print("type decoded = %s" % type (decoded))
            print (json.dumps(decoded, sort_keys=True, indent=4))
            if decoded['version'] == 1:
                print("old version %s" % decoded['version'] )
                reply = CreateVersion1Response(decoded['numberOfRecords'], connlocal)

            if decoded['version'] == 2:
                print("new version %s" % decoded['version'] )
                ConfigReader.g_config.SetIpAddressesIfEmpty(decoded['xDripIpAddresses'])
                reply = CreateVersion2Response(decoded, connlocal)
            
            print ("reply = %s" % reply)
            # We should probably call connlocal.shutdown(socket.SHUT_WR), but for historical reasons, 
            # we send an empty string, and the other side will close the connection.
            reply = reply + "\n"

            connlocal.sendall(bytes(reply, 'ascii'))
            
        connlocal.close()

    except Exception as e:
        print ("Exception in clientThread: ", e)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)

def CreateListeningSocket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    print ('Socket created')

    # Bind socket to local host and port

    try:
        print(ConfigReader.g_config.host)
        s.bind((ConfigReader.g_config.host, ConfigReader.g_config.port))
    except socket.error as msg:
        print ('Bind failed. Error Code : ' + str(msg))
        time.sleep(60)
        return

    s.listen(10)
    print ("Waiting for TCP/IP connections from xDrip.")

    while 1:
        conn, addr = s.accept()
        print ('Connected with ' + addr[0] + ':' + str(addr[1]))

        threading.Thread(target=clientThread, args=(conn,)).start()

def CreateListeningSocketWrapper():
    while 1:
        try:
            CreateListeningSocket()
        except Exception as exception :
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            #???? log(log_file, 'CreateListeningSocketWrapper caught exception in while loop' + str(exception) + exception.__class__.__name__)
            time.sleep(60)


''' ------------------------------------------------------------------------------'''


#if not ConfigReader.g_config.bt_mac_addreses:
#    scan.ScanForTomatoOrDie() Add here code to check that xdrip ip is set.

try:
    MongoWrapper.write_log_to_mongo(log_file, "starting program")
except Exception as exception :  
    log(log_file, 'Mongo caught exception in first write ' + str(exception) + exception.__class__.__name__)

try:
    mongo_wrapper = MongoWrapper(log_file)
    mongo_wrapper.start()
except Exception as exception :  
    # This is a critical failure, we will continue going up, but in a very bad state. Consider quiting the program
    log(log_file, 'WTF, caught exception in MongoWrapper cration ' + str(exception) + exception.__class__.__name__)               
               

# start the listener thread
try:
    threading.Thread(target= CreateListeningSocketWrapper).start()
except Exception as exception :  
    # This is a critical failure, we will continue going up, but in a very bad state. Consider quiting the program
    log(log_file, 'WTF, caught exception in opening listening socket ' + str(exception) + exception.__class__.__name__)
               

# fields that are needed in order to ask for retries, but not more then 3 times in 5 minutes.               
class MultipleRetries():
    def __init__(self):
        self.multyRetriesStart_ = time.time()
        self.numberOfCrcErrors_ = 0
        self.NumberOfDiscnections_ = 0
        
    def reinit(self):
        self.multyRetriesStart_ = time.time()
        self.numberOfCrcErrors_ = 0
        self.NumberOfDiscnections_ = 0

    # returns true, if one is allowed to send again.      
    def tryAgainAlowed(self):
        logging.info('tryAgainAlowed numberOfCrcErrors_ = %d NumberOfDiscnections_ = %d', self.numberOfCrcErrors_ , self.NumberOfDiscnections_)
        if(self.numberOfCrcErrors_ + self.NumberOfDiscnections_) < 4:
            logging.info('We are still allowed to retry ')
            return True
        if time.time() - self.multyRetriesStart_ < 300:
            logging.info('We have too many failures and not enough time passed, failing request')
            MongoWrapper.write_log_to_mongo(log_file, "Too many errors, waiting 5 minutes")
            return False
        logging.info('We have too many failures but time has passed - resetting count')
        self.reinit()
        return True
        
    def crcErrorHappened(self):
        self.numberOfCrcErrors_ += 1

               
class DataCollector():
    def __init__(self):
        self.data_ =  bytes()
        self.recviedEnoughData_ = False
        self.lastReceiveTimestamp_ = time.time()
        self.multipleRetries_ = MultipleRetries()
        
        
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
        self.data_ =  bytes()
        self.recviedEnoughData_ = False
        self.lastReceiveTimestamp_ = time.time()
        
        
    def AcumulateData(self, new_data, CharacteristicSend):
        if time.time() - self.lastReceiveTimestamp_ > 3:
            # Too much time from last time
            logging.info('restarting since time from last packet is %d %s %d', (time.time() - self.lastReceiveTimestamp_), ' already acumulated ', len(self.data_))
            self.reinit()
            
        self.lastReceiveTimestamp_ = time.time()
        

        self.data_ = self.data_ + new_data
        logging.info('recieved %d total = %s' ,len(new_data), binascii.b2a_hex(self.data_))
        self.AreWeDone(CharacteristicSend)
        
    def AreWeDone(self, CharacteristicSend):
        if self.recviedEnoughData_:
            return
        if len(self.data_) < 46:
            return
        self.recviedEnoughData_ = True
        print('we have enough data len = ', len(self.data_))
        checksom_ok = False
        #logging.info('checksum_ok = %s' % checksom_ok)
        
        captured_time = int(time.time() * 1000)
        DebugInfo = '%s %s %s' % (socket.gethostname(), time.strftime('%d-%m-%Y %H:%M:%S', time.localtime(captured_time / 1000)), 'libre2')
        
        sqw = sqllite3_wrapper( )
        sqw.InsertReading(self.data_, captured_time, checksom_ok, DebugInfo)
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
        checksum_ok1 = self.CheckCRC16(data, 0 ,24)
        print('checksum_ok1 = ', checksum_ok1)
        checksum_ok2 = self.CheckCRC16(data, 24 ,296)
        print('checksum_ok2 = ', checksum_ok2)
        checksum_ok3 = self.CheckCRC16(data, 320 ,24)
        print('checksum_ok3 = ', checksum_ok3)
        return checksum_ok1 & checksum_ok2 & checksum_ok3

    # Input is 8 bytes
    def decodeSerialNumber(self, input):
        lookupTable = [
                        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                        "A", "C", "D", "E", "F", "G", "H", "J", "K", "L",
                        "M", "N", "P", "Q", "R", "T", "U", "V", "W", "X",
                        "Y", "Z"
                ]
                
        uuidShort = [0, 0, 0, 0, 0, 0, 0, 0]

        for i in range(2,8):
            uuidShort[i - 2] = input[7 - i]
        uuidShort[6] = 0x00
        uuidShort[7] = 0x00

        #print("uuidShort", uuidShort)

        binary = ""
        for i in range(0,8):
            binS =  (format(uuidShort[i], '08b'))# str(uuidShort[i]).zfill(8) #String.format("%8s", Integer.toBinaryString(uuidShort[i] & 0xFF)).replace(' ', '0');
            binary += binS;

        #print(binary)

        v = "0"
        pozS = [0, 0, 0, 0, 0]
        for i in range(0, 10): 
            for k in range(0, 5):
                pozS[k] = binary[(5 * i) + k]
            #print("type pos", type(pozS[0]))
            value = (ord(pozS[0]) - ord('0')) * 16 + (ord(pozS[1]) - ord('0')) * 8 + (ord(pozS[2]) - ord('0')) * 4 + (ord(pozS[3]) - ord('0')) * 2 + (ord(pozS[4]) - ord('0')) * 1
            v += lookupTable[value]
            #print(value)

        #print("Sensor serial number is ", v)
        return v


data_collector = DataCollector() 
        
        

class MyDelegate(btle.DefaultDelegate):
    def __init__(self, CharacteristicSend):
        btle.DefaultDelegate.__init__(self)
        print('Init called.')
        # ... initialise here
        self.count = 0
        self.CharacteristicSend_  = CharacteristicSend

    def handleNotification(self, cHandle, data):
        # ... perhaps check cHandle
        # ... process 'data'
        #print ('notification called count = ', self.count , strftime("%Y-%m-%d %H:%M:%S", gmtime()),binascii.b2a_hex(data))
        data_collector.AcumulateData(data, self.CharacteristicSend_)
        #print(type(data))
        self.count +=1
        if self.count % 10 == 0:
            print (self.count)

# Using a global here since ReadData never returns.
g_remote_mac = None

def ReadBLEData():
    global g_remote_mac 
    ScanForAbbottUntilFound(g_remote_mac)
    #time.sleep(1)
    
    print ("Connecting to xDrip...")
    connection_params = ReadDeviceAddresses(True)
    if not connection_params:
        return
    g_remote_mac = connection_params['MacAddress'].lower()
    logging.info("Connecting to btDevice...")
    dev = btle.Peripheral(g_remote_mac)

    logging.info("Connected - Services are:")
    for svc in dev.services:
        print (str(svc))
    
    NRF_UART_SERVICE = btle.UUID("0000fde3-0000-1000-8000-00805f9b34fb") # nrfDataService
 
    print ("charterstics...")
    nrfGattService = dev.getServiceByUUID(NRF_UART_SERVICE)
    for ch in nrfGattService.getCharacteristics():
         print (str(ch))

    NRF_UART_RX = btle.UUID("0000f001-0000-1000-8000-00805f9b34fb")
    NRF_UART_TX = btle.UUID("0000f002-0000-1000-8000-00805f9b34fb")
    CLIENT_CHARACTERISTIC_CONFIG =  btle.UUID("00002902-0000-1000-8000-00805f9b34fb")
    
    nrfGattCharacteristic = nrfGattService.getCharacteristics(NRF_UART_TX)
    print ("nrfGattCharacteristic = ", nrfGattCharacteristic)
    #print  nrfGattCharacteristic.supportsRead()
    print (nrfGattCharacteristic[0].propertiesToString())

    bdescriptor =  nrfGattCharacteristic[0].getDescriptors(CLIENT_CHARACTERISTIC_CONFIG)
    bdescriptor[0].write(struct.pack('<bb', 0x01, 0x00), False)
    CharacteristicSend = nrfGattService.getCharacteristics(NRF_UART_RX)[0]

    dev.setDelegate( MyDelegate(CharacteristicSend) )
    
    connection_params = ReadDeviceAddresses(False)
    str1 = base64.decodebytes(connection_params['BtUnlockBuffer'].encode('ascii'))
    print(str1)
    CharacteristicSend.write(str1)
       
    time.sleep(1.0) # Allow sensor to stabilize
    
    while True:
        dev.waitForNotifications(1.0)

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(asctime)s %(message)s')
        
#btle.Debugging = True

def ScanForAbbottUntilFound(remote_mac):
    if not remote_mac:
        return
    if os.geteuid() !=0:
        print ('you need root permission for ble scanning.')
        print ('please run the program with sudo ...')
        time.sleep(10)
        return
    start = datetime.datetime.now()    
    while(True):
        if timedelta(minutes=10) + start < datetime.datetime.now():
            logging.info("Leaving ScanForAbbottUntilFound because of timeout")
            return
        scanner = btle.Scanner()
        #print('scanning for miaomiao devices')
        try: 
            devices = scanner.scan(1)
        except btle.BTLEManagementError as err:
            logging.error('scanner.scan() raised exception ' + str(err));
            return  
        
        #print('devices found:')
        for device in devices:
            name = device.getValueText(9)
            if name  and 'ABBOTT' in name and remote_mac == str(device.addr): #???? Pass the full name here
                logging.info( "Sensor found %s %s %s %s", str(device.addr),  device.addrType, name, device.rssi)    
                return


def ReadDeviceAddresses(read_only):
    if not ConfigReader.g_config.xdrip_ip_addresses:
        print('no ConfigReader.g_config.xdrip_ip_addresses yet, will be solved when xDrip connects.')
        time.sleep(10)
        return 
    # Add code to verify config exists, and make sure errors are printed correctly.
    sha_1 = hashlib.sha1()
    sha_1.update(ConfigReader.g_config.api_secret.encode('utf-8'))
    headers = {'API-secret': sha_1.hexdigest()}
    response = requests.get("http://%s:17580/Libre2ConnectCode.json?ReadOnly=%s" % 
                               ( ConfigReader.g_config.xdrip_ip_addresses ,str(read_only).lower()),
                            headers=headers, timeout = 10 )
    
                            
    print (response.status_code, response.json(), type(response.json()))
    if response.status_code != 200:
        print('Error connecting to xDrip not continuing')
        raise ValueError('Error connecting to xDrip not continuing')
    
    return response.json()


while 1:
    try:
        ReadBLEData()
    except KeyboardInterrupt as keyboardInterrupt :
        log(log_file, 'caught exception KeyboardInterrupt:' + str(keyboardInterrupt))
        os.kill(os.getpid(), signal.SIGKILL)
        sys.exit(0)
    except btle.BTLEException as exception:
        logging.info('cought btle.BTLEException %s', exception.message)
    except Exception as exception :
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        log(log_file, 'caught exception in while loop: ' + str(exception) + exception.__class__.__name__  + 
            repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))

        
    time.sleep(3)
