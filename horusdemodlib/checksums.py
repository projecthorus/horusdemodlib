#
#   HorusLib - Checksumming functions
#

import crc
import logging
import struct
import unittest
from crc import Calculator,  Configuration


def mkCrcFun(type):
        calculator = Calculator(Configuration(
            16, 0x1021,0xffff
        ))
        if type == 'crc-ccitt-false':
            def check(data):
                return calculator.checksum(data)
        return check

def ukhas_crc(data:bytes) -> str:
    """
    Calculate the CRC16 CCITT checksum of *data*.
    
    (CRC16 CCITT: start 0xFFFF, poly 0x1021)
    """
    crc16 = mkCrcFun('crc-ccitt-false')

    return hex(crc16(data))[2:].upper().zfill(4)


def check_packet_crc(data:bytes, checksum:str='crc16', tail=True):
    """ 
    Attempt to validate a packets checksum, which is assumed to be present
    in the last few bytes of the packet.

    Support CRC types: CRC16-CCITT

    """

    if (checksum == 'crc16') or (checksum == 'CRC16') or (checksum == 'crc16-ccitt') or (checksum == 'CRC16-CCITT'):
        # Check we have enough data for a sane CRC16.
        if len(data) < 3:
            raise ValueError(f"Checksum - Not enough data for CRC16!")

        # Decode the last 2 bytes as a uint16
        _packet_checksum = struct.unpack('<H', data[-2:])[0] if tail else struct.unpack('<H', data[:2])[0]

        # Calculate a CRC over the rest of the data
        _crc16 = mkCrcFun('crc-ccitt-false')
        _calculated_crc = _crc16(data[:-2] if tail else data[2:])

        if _calculated_crc == _packet_checksum:
            return True
        else:
            logging.debug(f"Calculated: {hex(_calculated_crc)}, Packet: {hex(_packet_checksum)}")
            return False

    else:
        raise ValueError(f"Checksum - Unknown Checksym type {checksum}.")


def add_packet_crc(data:bytes, checksum:str='crc16', tail=True):
    """ 
    Add a CRC onto the end of provided bytes

    Support CRC types: CRC16-CCITT

    """

    if (checksum == 'crc16') or (checksum == 'CRC16') or (checksum == 'crc16-ccitt') or (checksum == 'CRC16-CCITT'):
        # Calculate a CRC over the data
        _crc16 = mkCrcFun('crc-ccitt-false')
        _calculated_crc = _crc16(data)

        _packet_crc = struct.pack('<H', _calculated_crc)
        if tail:
            return data + _packet_crc
        else:
            return _packet_crc + data


    else:
        raise ValueError(f"Checksum - Unknown Checksym type {checksum}.")

class HorusChecksumTests(unittest.TestCase):
    def test_crc16_decoder(self):
        tests = [
        ['crc16', b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', True],
        ['crc16', b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', False],
        ['crc16', b'\x01\x12\x02\x00\x02\xbc\xeb!AR\x10\x00\xff\x00\xe1\x7e', True],
        #           id      seq_no  HH   MM  SS  lat             lon             alt    spd  sat tmp bat custom data
        ['crc16', b'\xFF\xFF\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe8\x82', True],
    ]
        
        for _test in tests:
            _format = _test[0]
            _input = _test[1]
            _output = _test[2]

            with self.subTest(format=_format,input=_input,output=_output):
                if _output == 'error':
                    with self.assertRaises(ValueError) as context:
                        _decoded = _decoded = check_packet_crc(_input, _format)
                else:
                    _decoded = _decoded = check_packet_crc(_input, _format)
                logging.debug(f"Packet: {_input}. CRC OK: {_decoded}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()