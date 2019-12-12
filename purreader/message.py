class PURPacket:
    '''
    Reader host protocol message packet
    '''
    def __init__(self, cmdBytes=b'', pldBytes=b'', msgBytes=b''):
        '''
        Converts either command and payload bytes to message bytes 
        or vice versa, depending which has content

        :param cmdBytes: byte array of first command byte and second command byte
        :param pldBytes: byte array of payload bytes
        :param msgBytes: byte array of message bytes with checksum
        '''
        self.cmdBytes = cmdBytes
        self.pldBytes = pldBytes
        self.msgBytes = msgBytes
        # convert
        if self.cmdBytes:
            self.msgBytes = self.createMsg(self.cmdBytes, self.pldBytes)
        elif self.msgBytes:
            self.cmdBytes, self.pldBytes = self.parseMsg(self.msgBytes)
        else:
            raise AttributeError('Either command bytes or message bytes must be passed')
    

    def _prettyBytes(self, byteArr):
        return ' '.join('{:02X}'.format(b) for b in byteArr)
    

    def __repr__(self):
        return 'PURMessage({}, {}, {})'.format(
            self.cmdBytes, self.pldBytes, self.msgBytes)
    

    def __str__(self):
        if self.cmdBytes:
            return 'command: {}{}{}'.format(self._prettyBytes(self.cmdBytes), 
                ' ("{}")'.format(cmdDescr[self.cmdBytes]) if self.cmdBytes in cmdDescr else '', 
                ', payload: {}'.format(self._prettyBytes(self.pldBytes)) if self.pldBytes else '')
        else:
            return 'message: {}'.format(self._prettyBytes(self.msgBytes))
    

    def calcChecksum(self, msgBytes):
        '''
        Calculates the checksum over message bytes

        :msgBytes: message bytes
        :returns: checksum integer
        '''
        checksum = msgBytes[0]
        for byte in msgBytes[1:]:
            checksum ^= byte # XOR all bytes in message together
        
        return checksum


    def createMsg(self, cmdBytes, pldBytes=b''):
        '''
        Builds a reader message with command and optional payload parameters

        :param cmdBytes: byte array of first command byte and second command byte
        :param pldBytes: byte array of payload bytes
        :returns: message bytes with checksum
        '''
        msgBytes = b'RFE' # start

        msgBytes += b'\x01' # start of command bytes
        msgBytes += cmdBytes # command bytes

        msgBytes += b'\x02' # start of length
        msgBytes += bytes([len(pldBytes)]) # length byte

        if pldBytes:
            msgBytes += b'\x03' # start of payload
            msgBytes += pldBytes # payload bytes
        
        msgBytes += b'\x04' # start of checksum
        checksumBytes = bytes([self.calcChecksum(msgBytes)]) # calculate checksum
        msgBytes += checksumBytes # append checksum byte
        return msgBytes
    

    def parseMsg(self, msgBytes):
        '''
        Parses command and payload from message bytes

        :msgBytes: message bytes
        :returns: tuple with (byte array of command, byte array of payload)
        '''
        if len(msgBytes) < 8:
            raise SyntaxError('Message too short')

        if self.calcChecksum(msgBytes) != 0:
            raise ValueError('Wrong checksum')
        
        # check message start
        if msgBytes[:4] != b'RFE\x01':
            raise SyntaxError('Wrong message start')
        msgBytes = msgBytes[4:]
        
        # get command bytes
        cmdBytes = msgBytes[:2]
        msgBytes = msgBytes[2:]
        
        # check payload length start
        if msgBytes[0] != 0x02:
            raise SyntaxError('Wrong payload length start')
        msgBytes = msgBytes[1:]

        # get number of payload bytes
        payloadLen = msgBytes[0]
        msgBytes = msgBytes[1:]

        if payloadLen > 0:
            # check payload start
            if msgBytes[0] != 0x03:
                raise SyntaxError('Wrong payload start')
            msgBytes = msgBytes[1:]
            
            # get payload bytes
            pldBytes = msgBytes[:payloadLen]
            msgBytes = msgBytes[payloadLen:]
        else:
            pldBytes = b''

        return (cmdBytes, pldBytes)


# payload of PUR packet may contain a return code byte
retCodeDescr = {
    0x00: 'Everything went fine.', 
    0x01: 'The operation is pending, the result will be sent later on.', 
    0x50: 'Operation is not supported on this reader.', 
    0x51: 'Unkown error.', 
    0x52: 'The operation could not be executed.', 
    0x53: 'The reader could not write the value.', 
    0x54: 'The function was called with the wrong parameter count.', 
    0x55: 'The function was called with the wrong parameter.', 
    0xA0: 'The reader could not reach the tag.', 
    0xA1: 'The specified memory space is not valid.', 
    0xA2: 'The specified memory space is locked.', 
    0xA3: 'The tag has too less power.', 
    0xA4: 'The specified password is wrong.'
}


# command bytes description
cmdDescr = {
    b'\x01\x01': 'Get-Serial Number', 
    b'\x01\x02': 'Get-Reader Type', 
    b'\x01\x03': 'Get-Hardware Revision', 
    b'\x01\x04': 'Get-Software Revision', 
    b'\x01\x05': 'Get-Bootloader Revision', 
    b'\x01\x06': 'Get-Current-System', 
    b'\x01\x07': 'Get-Current-State', 
    b'\x01\x08': 'Get-Status-Register', 
    b'\x01\x10': 'Get-Antenna-Count', 
    b'\x02\x01': 'Get-Attenuation', 
    b'\x02\x02': 'Get-Frequency', 
    b'\x02\x03': 'Get-Sensitivity', 
    b'\x02\x04': 'Get-LBT-Params', 
    b'\x02\x81': 'Set-Attenuation', 
    b'\x02\x82': 'Set-Frequency', 
    b'\x02\x83': 'Set-Sensitivity', 
    b'\x02\x84': 'Set-LBT-Params', 
    b'\x03\x01': 'Reboot', 
    b'\x03\x02': 'Set-Heart-Beat', 
    b'\x03\x03': 'Set-Antenna-Power', 
    b'\x03\x20': 'Restore-Factory-Settings', 
    b'\x03\x21': 'Save-Settings-Permanent', 
    b'\x03\x30': 'Set-Param', 
    b'\x03\x31': 'Get-Param', 
    b'\x03\x32': 'Set-Device-Name', 
    b'\x03\x33': 'Get-Device-Name', 
    b'\x03\x34': 'Set-Device-Location', 
    b'\x03\x35': 'Get-Device-Location', 
    b'\x04\x01': 'Set-Tag-Mode', 
    b'\x04\x02': 'Get-Current-Tag-Mode', 
    b'\x04\x03': 'Get-Tag-Function-List', 
    b'\x05\x01': 'Get-GPIO-Caps', 
    b'\x05\x02': 'Get-GPIO-Direction', 
    b'\x05\x03': 'Set-GPIO-Direction', 
    b'\x05\x04': 'Get-GPIO', 
    b'\x05\x05': 'Set-GPIO', 
    b'\x05\x06': 'Clear-GPIO', 
    b'\x06\x01': 'Set-Antenna-Sequence', 
    b'\x06\x02': 'Get-Antenna-Sequence', 
    b'\x06\x03': 'Set-Working-Antenna', 
    b'\x06\x04': 'Get-Working-Antenna', 
    b'\x10\x01': 'Activate-Notifications', 
    b'\x10\x02': 'Deactivate-Notifications', 
    b'\x10\x03': 'Get-Active-Notifications', 
    b'\x50\x01': 'Inventory-Single', 
    b'\x50\x02': 'Inventory-Cyclic', 
    b'\x50\x03': 'Read-From-Tag', 
    b'\x50\x04': 'Write-To-Tag', 
    b'\x50\x05': 'Lock-Tag', 
    b'\x50\x06': 'Kill-Tag', 
    b'\x50\x10': 'Custom-Tag-Command', 
    b'\x50\x20': 'Read-Multiple-From-Tag', 
    b'\x90\x01': 'Heart-Beat-Interrupt', 
    b'\x90\x02': 'Inventory-Cyclic-Interrupt', 
    b'\x90\x03': 'State-Changed-Interrupt', 
    b'\x90\x04': 'Status-Reg-Changed-Interrupt', 
    b'\x90\x05': 'Boot-Up-Finished', 
    b'\x90\x06': 'Notification-Interrupt', 
    b'\x90\x08': 'Operation-Result-Interrupt', 
    b'\x90\x09': 'GPIO-Values-Changed-Interrupt'
}


# tag backscatter link frequencies
tagFreqsKHz = {
    0x00: 40, 
    0x01: 80, 
    0x02: 160, 
    0x03: 213, 
    0x04: 256, 
    0x05: 320
}


# tag encoding
tagEncodings = {
    0x00: 'FM0', 
    0x01: 'M2', 
    0x02: 'M4', 
    0x03: 'M8'
}
