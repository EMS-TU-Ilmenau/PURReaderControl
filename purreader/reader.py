import serial # to communicate with the reader physically
from .message import PURPacket, retCodeDescr, tagFreqsKHz, tagEncodings # to build and reading messages
import struct # for parsing parameters from messages
import time # for waiting
import logging # for logging debug messages


class PURReader:
    '''
    Reader controller
    '''
    def __init__(self, interface):
        '''
        :param interface: serial port interface string
        '''
        self.dev = serial.Serial(interface, 9600, timeout=2)
        self.log = logging.getLogger(self.__class__.__name__)
    

    def __del__(self):
        if hasattr(self, 'dev'):
            # implement controlled stop here
            self.dev.close()
    

    def send(self, pkg, check=False):
        '''
        Sends a message to the reader

        :param pkg: PURPacket packet object to send
        :param check: should be set to True when response contains return code
        :returns: response PURPacket packet object(s)
        '''
        # send packet
        self.log.debug('Sending: {}'.format(pkg))
        self.dev.write(pkg.msgBytes)

        # receive
        respBytes = self.dev.read(1) # wait until something is in buffer
        time.sleep(0.01) # give time for the reader to write more in buffer
        respBytes += self.dev.read(self.dev.in_waiting)

        # get all command related packets
        start = pkg.msgBytes[:6] # bytes R,F,E,0x01,<cmd1>,<cmd2>
        respPkgs = [PURPacket(msgBytes=start+part) for part in respBytes.split(start)[1:]]
        self.log.debug('Received: '+'\n'.join(str(p) for p in respPkgs))
        
        # check if command was successful
        if check:
            for respPkg in respPkgs:
                self.checkResp(respPkg)
        
        # return
        if len(respPkgs) == 1:
            return respPkgs[0]
        else:
            return respPkgs
    

    def checkResp(self, respPkg):
        '''
        Checks first byte of packet payload for return code. 
        If not 0, an exception with the error description is thrown.

        :param respPkg: received package from reader
        '''
        if respPkg.pldBytes:
            code = respPkg.pldBytes[0]
            if code != 0:
                if code in retCodeDescr:
                    raise IOError('Problem with packet {}: {}'.format(
                        respPkg, retCodeDescr[code]))
    

    @property
    def antCount(self):
        '''
        Gets number of reader antennas
        '''
        resp = self.send(PURPacket(b'\x01\x10'))
        return resp.pldBytes[1]
    

    @property
    def attnDB(self):
        '''
        Gets attenuation in dB
        '''
        resp = self.send(PURPacket(b'\x02\x01'), True)
        # maximum, current attenuation
        _, curAttn = struct.unpack('!HH', resp.pldBytes[1:])
        return curAttn
    

    @attnDB.setter
    def attnDB(self, val):
        '''
        Sets attenuation in dB
        '''
        self.send(PURPacket(b'\x02\x81', struct.pack('!H', val)), True)
    

    @property
    def freqKHz(self):
        '''
        Gets frequency in kHz
        '''
        resp = self.send(PURPacket(b'\x02\x02'), True)
        # mode (0 = random hopping, 1 = static), maximum frequency count, current frequency count
        _, _, numFreqs = struct.unpack('!BBB', resp.pldBytes[1:4])
        # frequency list
        freqs = [struct.unpack('!I', b'\x00'+resp.pldBytes[4+iF*3:4+iF*3+3])[0] for iF in range(numFreqs)]
        if len(freqs) > 1:
            return freqs
        else:
            return freqs[0]
    

    @freqKHz.setter
    def freqKHz(self, val):
        '''
        Sets frequency in kHz
        '''
        if isinstance(val, (tuple, list)):
            # expect frequency list in kHz
            # we use random hopping in this case
            freqs = [int(f) for f in val]
            payload = struct.pack('!BB', 1, len(freqs)) # mode 1 (random) and n frequencies
            for freq in freqs:
                payload += struct.pack('!I', freq)[1:] # add frequency as 3 bytes
        elif isinstance(val, (int, float)):
            # expect 1 frequency in kHz
            freq = int(val)
            payload = struct.pack('!BB', 0, 1) # mode 0 (static) and 1 frequency
            payload += struct.pack('!I', freq)[1:] # add frequency as 3 bytes
        else:
            raise SyntaxError('freqKHz must be either a single frequency or a list of frequencies')
        
        self.send(PURPacket(b'\x02\x82', payload), True)


    @property
    def sensDBm(self):
        '''
        Gets sensitivity in dBm
        '''
        resp = self.send(PURPacket(b'\x02\x03'), True)
        # maximum sensitivity, minimum sensitivity, current sensitivity
        _, _, curSens = struct.unpack('!hhh', resp.pldBytes[1:])
        return curSens
    

    @sensDBm.setter
    def sensDBm(self, val):
        '''
        Sets sensitivity in dBm
        '''
        self.send(PURPacket(b'\x02\x83', struct.pack('!h', val)), True)
    

    def setParam(self, addr, valBytes):
        '''
        Sets a device specific parameter.
        See "Reader-Host-Protocol – PUR-Extension"

        :param addr: address of the parameter
        :param valBytes: parameter value bytes
        '''
        payload = struct.pack('!HB', addr, len(valBytes))
        payload += valBytes
        self.send(PURPacket(b'\x03\x30', payload), True)
    

    def getParam(self, addr):
        '''
        Gets a device specific parameter.
        See "Reader-Host-Protocol – PUR-Extension"

        :param addr: address of the parameter
        :returns: parameter value bytes
        '''
        resp = self.send(PURPacket(b'\x03\x31', struct.pack('!H', addr)), True)
        size = resp.pldBytes[1]
        return resp.pldBytes[2:2+size]
    

    @property
    def session(self):
        '''
        Gets inventory session. 
        Can be 0, 1, 2 or 3
        '''
        return self.getParam(0x0028)[0]
    

    @session.setter
    def session(self, val):
        '''
        Sets inventory session
        '''
        self.setParam(0x0028, struct.pack('!B', val))
    

    @property
    def modDepth(self):
        '''
        Gets reader modulation depth. 
        Can be 0...100 %
        '''
        return self.getParam(0x0022)[0]
    

    @modDepth.setter
    def modDepth(self, val):
        '''
        Sets reader modulation depth
        '''
        self.setParam(0x0022, struct.pack('!B', val))
    

    @property
    def blfKHz(self):
        '''
        Gets tag backscatter link frequency. 
        Can be 40, 80, 160, 213, 256 or 320 kHz
        '''
        blfKey = self.getParam(0x0020)
        return tagFreqsKHz[blfKey[0]]
    

    @blfKHz.setter
    def blfKHz(self, val):
        '''
        Sets tag backscatter link frequency
        '''
        val = int(val)
        # get key (lookup byte) for value (frequency)
        for blfKey, blfVal in tagFreqsKHz.items():
            if val == blfVal:
                self.setParam(0x0020, struct.pack('!B', blfKey))
                return
        
        raise ValueError('Invalid backscatter frequency. Can be: '+
            ', '.join('{} kHz'.format(f) for f in tagFreqsKHz.values()))
    

    @property
    def encoding(self):
        '''
        Gets tag backscatter link encoding. 
        Can be "FM0", "M2", "M4" or "M8"
        '''
        encKey = self.getParam(0x0021)
        return tagEncodings[encKey[0]]
    

    @encoding.setter
    def encoding(self, val):
        '''
        Sets tag backscatter link encoding
        '''
        # get key (lookup byte) for value (string)
        for encKey, encVal in tagEncodings.items():
            if val == encVal:
                self.setParam(0x0021, struct.pack('!B', encKey))
                return
        
        raise ValueError('Invalid backscatter encoding. Can be: '+
            ', '.join(e for e in tagEncodings.values()))
    

    def enableOutput(self, enable):
        '''
        Sets antenna power on or off

        :param enable: True or False
        '''
        state = 1 if enable else 0
        self.send(PURPacket(b'\x03\x03', struct.pack('!B', state)), True)
    

    def reportRSSI(self, enable):
        '''
        Enables the report of Q/I RSSI for detected tag

        :param enable: True or False
        '''
        state = 1 if enable else 0
        self.setParam(0x0002, struct.pack('!B', state))
    

    def parseTagreports(self, recPkgs):
        '''
        Parses tagreports from inventory packets

        :param recPkgs: one or more packets from single or cyclic inventory
        :returns: list of dictionaries with meta infos of detected tags
        '''
        if not isinstance(recPkgs, list):
            recPkgs = [recPkgs] # unify response because there might be more than 1 package
        
        # parse tags
        tags = []
        collectedIds = 0
        idCount = 0
        for pkg in recPkgs:
            # packet meta data
            idCount, pkgIdCount = struct.unpack('!BB', pkg.pldBytes[1:3])
            collectedIds += pkgIdCount # tag ids in this packet
            
            # bytes for detected tag info structures
            tagsBytes = pkg.pldBytes[3:]
            for _ in range(pkgIdCount):
                # parse tag infos
                # check tag id start
                iStart = tagsBytes.find(0x01)
                tagsBytes = tagsBytes[iStart+1:]
                
                # get id length
                idLen = tagsBytes[0]
                tagsBytes = tagsBytes[1:]

                # get id
                tagID = ''.join('{:02X}'.format(b) for b in tagsBytes[:idLen])
                tagsBytes = tagsBytes[idLen:]

                # check RSSI start
                if tagsBytes[0] != 0x02:
                    raise SyntaxError('Wrong RSSI start')
                tagsBytes = tagsBytes[1:]

                # get RSSI
                rssiQ, rssiI = struct.unpack('!BB', tagsBytes[:2])
                tagsBytes = tagsBytes[2:]

                tagData = {
                    tagID: {
                        'rssiI': rssiI, 
                        'rssiQ': rssiQ
                    }
                }
                tags.append(tagData)
        
        if collectedIds != idCount:
            raise IOError('Only packets for {} out of {} tags where received'.format(collectedIds, idCount))

        return tags        
    

    def singleInventory(self):
        '''
        Performs a single inventory and returns the tags detected 
        with meta infos
        '''
        self.reportRSSI(True) # tags shall be reported with RSSI
        resp = self.send(PURPacket(b'\x50\x01'), True) # start inventory
        tags = self.parseTagreports(resp)
        self.log.info('{} tags found'.format(len(tags)))
        return tags
