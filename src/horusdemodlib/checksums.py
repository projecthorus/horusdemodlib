#
#   HorusLib - Checksumming functions
#

import crcmod
import logging
import struct



def ukhas_crc(data:bytes) -> str:
    """
    Calculate the CRC16 CCITT checksum of *data*.
    
    (CRC16 CCITT: start 0xFFFF, poly 0x1021)
    """
    crc16 = crcmod.predefined.mkCrcFun('crc-ccitt-false')

    return hex(crc16(data))[2:].upper().zfill(4)


def check_packet_crc(data:bytes, checksum:str='crc16'):
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
        _packet_checksum = struct.unpack('<H', data[-2:])[0]

        # Calculate a CRC over the rest of the data
        _crc16 = crcmod.predefined.mkCrcFun('crc-ccitt-false')
        _calculated_crc = _crc16(data[:-2])

        if _calculated_crc == _packet_checksum:
            return True
        else:
            logging.debug(f"Calculated: {hex(_calculated_crc)}, Packet: {hex(_packet_checksum)}")
            return False

    else:
        raise ValueError(f"Checksum - Unknown Checksym type {checksum}.")



if __name__ == "__main__":

    # Setup Logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=logging.DEBUG
    )

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

        _decoded = check_packet_crc(_input, _format)

        print(f"Packet: {_input}. CRC OK: {_decoded}")
        assert(_decoded == _output)

    print("All tests passed!")