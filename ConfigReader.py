#  File for reading configuration from ini file.
import configparser
import os
import inspect

# Hold configuration data explicitly.
class Config:
    db_uri = None
    db_name = None
    collection_name = None
    host = None
    port = None
    bt_mac_addreses = None

    def GetFileName(self):
        path = os.path.dirname(os.path.abspath(inspect.stack()[0][1]))
        file_name = path+os.sep+'config.cfg'
        return file_name
    
    def OpenFile(self):
        config = configparser.ConfigParser()
        
        try:
            file = open(self.GetFileName())
        except OSError as e:
            print('ERROR: Reading config file %s failed. Please copy config_example.cfg and change the values accordingly.' % file_name)
            print ('Program exiting')
            exit(1)
        config.read_file(file)
        return config
    
    def UpdateSection(self, section, option, value ):
        config = self.OpenFile()
        config.set(section,option, value)
        cfgfile = open(self.GetFileName(),'w')
        print('cfgfile = ', cfgfile)
        config.write(cfgfile)
        cfgfile.close()
        g_config.ReadConfig()
        
    
    def ReadConfig(self):
        
        config = configparser.ConfigParser()
        path = os.path.dirname(os.path.abspath(inspect.stack()[0][1]))
        file_name = path+os.sep+'config.cfg'
        try:
            file = open(file_name)
        except OSError as e:
            print('ERROR: Reading config file %s failed. Please copy config_example.cfg and change the values accordingly.' % file_name)
            print ('Program exiting')
            exit(1)
        config.read_file(file)
        print(config.sections())
        g_config.db_uri = config.get('MongoData', 'db_uri')
        g_config.db_name = config.get('MongoData', 'db_name')
        g_config.collection_name = config.get('MongoData', 'collection_name')
        
        g_config.host = config.get('TcpSockets', 'host')
        g_config.port = int(config.get('TcpSockets', 'port'))
        
        g_config.bt_mac_addreses = config.get('BTDevice', 'bt_mac_address')
    
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

g_config = Config()
g_config.ReadConfig() 


if __name__ == '__main__' :
    # any amount of code to exercise the functions
    # defined above
    print (g_config)