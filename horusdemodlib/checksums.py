#
#   HorusLib - Checksumming functions
#

import binascii
import logging
import struct
import unittest


def ukhas_crc(data:bytes) -> str:
    """
    Calculate the CRC16 CCITT checksum of *data*.
    
    (CRC16 CCITT: start 0xFFFF, poly 0x1021)
    """

    return hex(binascii.crc_hqx(data,0xffff))[2:].upper().zfill(4)


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
        _calculated_crc = binascii.crc_hqx(data[:-2] if tail else data[2:], 0xffff)

        if _calculated_crc == _packet_checksum:
            return True
        else:
            logging.debug(f"Calculated: {hex(_calculated_crc)}, Packet: {hex(_packet_checksum)}")
            return False

    else:
        raise ValueError(f"Checksum - Unknown Checksum type {checksum}.")


def add_packet_crc(data:bytes, checksum:str='crc16', tail=True):
    """ 
    Add a CRC onto the end of provided bytes

    Support CRC types: CRC16-CCITT

    """

    if (checksum == 'crc16') or (checksum == 'CRC16') or (checksum == 'crc16-ccitt') or (checksum == 'CRC16-CCITT'):
        # Calculate a CRC over the data
        _calculated_crc = binascii.crc_hqx(data,0xffff)

        _packet_crc = struct.pack('<H', _calculated_crc)
        if tail:
            return data + _packet_crc
        else:
            return _packet_crc + data


    else:
        raise ValueError(f"Checksum - Unknown Checksum type {checksum}.")

class HorusChecksumTests(unittest.TestCase):
    def test_crc16_decoder(self):
        tests = [
        ['crc16', True, b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', True],
        ['crc16', True, b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', False],
        ['crc16', True, b'\x01\x12\x02\x00\x02\xbc\xeb!AR\x10\x00\xff\x00\xe1\x7e', True],
        #           id      seq_no  HH   MM  SS  lat             lon             alt    spd  sat tmp bat custom data
        ['crc16', True, b'\xFF\xFF\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe8\x82', True],
        # Horus v3 packets, CRC is at the start
        ['crc16', False, b'\xd1\xa2:\x8a\x19\x17\x96}\x07\x9f\x02\x11@\n\x89}\xe5E\x97G\x99%|\x11\x14\x00c\xff\xd4S\xf81x\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', True],
        ['crc16', False, b'\xd1\xa2:\x8a\x19\x17\x96}\x07\x9f\x02\x11@\n\x89}\xe5E\x97G\x99%|\x11\x14\x00c\xff\xd4S\xf81x\x00\x00\x00\x00\x00\x01\x02\x03\x00\x00\x00\x00\x00\x00\x00', False]
    ]
        
        for _test in tests:
            _format = _test[0]
            _horusv3 = _test[1]
            _input = _test[2]
            _output = _test[3]

            with self.subTest(format=_format,input=_input,output=_output):
                if _output == 'error':
                    with self.assertRaises(ValueError) as context:
                        _decoded = _decoded = check_packet_crc(_input, _format, tail=_horusv3)
                else:
                    _decoded = _decoded = check_packet_crc(_input, _format, tail=_horusv3)
                logging.debug(f"Packet: {_input}. CRC OK: {_decoded}")

    def test_crc16_encoder(self):
        tests = [
        # Horus v2
        ['crc16', True, b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A', b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45'],
        # Horus v3 packets, CRC is at the start
        ['crc16', False, b':\x8a\x19\x17\x96}\x07\x9f\x02\x11@\n\x89}\xe5E\x97G\x99%|\x11\x14\x00c\xff\xd4S\xf81x\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', b'\xd1\xa2:\x8a\x19\x17\x96}\x07\x9f\x02\x11@\n\x89}\xe5E\x97G\x99%|\x11\x14\x00c\xff\xd4S\xf81x\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'],
    ]
        
        for _test in tests:
            _format = _test[0]
            _horusv3 = _test[1]
            _input = _test[2]
            _output = _test[3]

            with self.subTest(format=_format,input=_input,output=_output):
                if _output == 'error':
                    with self.assertRaises(ValueError) as context:
                        _decoded = _decoded = add_packet_crc(_input, _format, tail=_horusv3)
                else:
                    _decoded = _decoded = add_packet_crc(_input, _format, tail=_horusv3)
                logging.debug(f"Packet: {_input}. Packet+CRC: {_decoded}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()