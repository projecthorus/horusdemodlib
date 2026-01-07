#!/usr/bin/env python3
#
#   HorusDemodLib - Encoder helper functions
#

import _horus_api_cffi
import codecs
import datetime
import logging
import struct
import sys
from enum import Enum
import os
import logging
from .decoder import decode_packet, hex_to_bytes
from .checksums import add_packet_crc
import unittest

horus_api = _horus_api_cffi.lib

class Encoder():
    """
    Horus Binary Encoder class.

    Allows creation of a Horus Binary packet.

    """

    def __init__(
        self,
        libpath=f"",
    ):
        """
        Parameters
        ----------
        libpath : str
            Path to libhorus
        """


        # Init 
        horus_api.horus_l2_init()

    # in case someone wanted to use `with` style. I'm not sure if closing the modem does a lot.
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def close(self) -> None:
        """
        Closes Horus modem. Does nothing here.
        """
        pass

    # Wrappers for libhorus C functions that we need.

    def get_num_tx_data_bytes(self, packet_size) -> int:
        """
        Calculate the number of transmit data bytes (uw+packet+fec) for a given
        input packet size.
        """
        return horus_api.horus_l2_get_num_tx_data_bytes(int(packet_size))


    def horus_l2_encode_packet(self, packet):
        """
        Encode a packet using the Horus Binary FEC scheme, which:
        - Generates Golay (23,12) FEC for the packet
        - Adds this onto the packet contents, and interleaves/scrambles
        - Adds a unique word (0x2424) to the start.

        Packet input must be provided as bytes.
        """

        if type(packet) != bytes:
            raise TypeError("Input to encode_packet must be bytes!")

        _unencoded = _horus_api_cffi.ffi.new("char[]", packet)

        _encoded = _horus_api_cffi.ffi.new("char[]", self.get_num_tx_data_bytes(len(packet)))


        _num_bytes = int(horus_api.horus_l2_encode_tx_packet(_encoded, _unencoded, int(len(packet))))

        return (bytes(_horus_api_cffi.ffi.buffer(_encoded)), _num_bytes)


    def horus_l2_decode_packet(self, packet, num_payload_bytes):
        """
        Decode a Horus-Binary encoded data packet.

        The packet must be provided as bytes, and must have the 2-byte unique word (0x2424)
        at the start.

        The expected number of output bytes must also be provided (22 or 32 for Horus v1 / v2 respectively)
        """

        if type(packet) != bytes:
            raise TypeError("Input to encode_packet must be bytes!")

        _encoded = _horus_api_cffi.ffi.new("char[]", packet)

        _decoded = _horus_api_cffi.ffi.new("char[]", num_payload_bytes)


        horus_api.horus_l2_decode_rx_packet(_decoded, _encoded, num_payload_bytes)

        return bytes(_horus_api_cffi.ffi.buffer(_decoded))
    

    def bytes_to_4fsk_symbols(self, 
            packet,
            preamble = 8
        ):
        """
        Convert a sequence of bytes to a sequence of 4FSK symbols (0,1,2,3) for modulation.
        Also adds a preamble sequence, by default 8 bytes long.
        """

        # Prepend preamble
        preamble_bytes = b'\x1B' * preamble
        packet = preamble_bytes + packet


        symbols = []

        for x in range(len(packet)):
            current_byte = packet[x]
            for k in range(4):
                symbols.append((current_byte & 0xC0) >> 6)
                current_byte = current_byte << 2

        return symbols
    
    def bytes_to_onebitperbyte(self,
        packet,
        preamble = 8
    ):
        """
        Convert a sequence of bytes to a one-bit-per-yte sequence, for modulation
        using fsk_mod.
        Also adds a preamble sequence, by default 8 bytes long.

        This data, if written out to a file, can be encoded using the fsk_mod utility, e.g.
        ./fsk_mod 4 48000 100 1000 270 onebitperbyte.bin test4fsk.raw
        produces a 48000 Hz Sample rate, Signed 16-bit output.
        """

        # Prepend preamble
        preamble_bytes = b'\x1B' * preamble
        packet = preamble_bytes + packet

        output = b''
        # Probably a faster way of doing this
        for x in range(len(packet)):
            current_byte = packet[x]
            for x in range(8):
                if (current_byte & 0x80) == 0x80:
                    output += b'\x01'
                else:
                    output += b'\x00'
                current_byte = current_byte << 1

        return output




    def create_horus_v2_packet(self,
            payload_id = 256,
            sequence_number = 0,
            # Packet time, provided as a datetime object
            time_dt = datetime.datetime.now(datetime.timezone.utc),
            # Optional - provide time as hours/minutes/seconds
            hours = None,
            minutes = None,
            seconds = None,
            # Payload position
            latitude = 0.0,
            longitude = 0.0,
            altitude = 0.0,
            speed = 0.0,
            satellites = 0,
            temperature = 0.0,
            battery_voltage = 0.0,
            # Default fields used for the 'custom' section of the packet.
            ascent_rate = 0.0,
            ext_temperature = 0.0,
            ext_humidity = 0.0,
            ext_pressure = 0.0,
            # Alternate custom data - must be bytes, and length=9
            custom_data = None,
            # Debugging options
            return_uncoded = False # Do not apply FEC/scrambling/whitening to packet
        ):
        """
        Create and encode a Horus V2 Data Packet.
        """

        # Sanity check input data.
        if payload_id < 256 or payload_id > 65535:
            raise ValueError("Invalid Horus v2 Payload ID. (Must be 256-65535)")
        
        # Clip sequence number
        sequence_number = int(sequence_number) % 65536

        if (hours is not None) and (minutes is not None) and (seconds is not None):
            # We have been provided time as separate H/M/S data
            # Do some clipping on this data
            hours = int(hours)
            if hours < 0:
                hours = 0
            elif hours > 23:
                hours = 23

            minutes = int(minutes)
            if minutes < 0:
                minutes = 0
            elif minutes < 59:
                minutes = 59

            seconds = int(seconds)
            if seconds < 0:
                seconds = 0
            elif seconds > 59:
                seconds = 59
        else:
            # No separate time data provided
            # Try and extract HHMMSS from datetime object
            try:
                hours = int(time_dt.hour)
                minutes = int(time_dt.minute)
                seconds = int(time_dt.second)
            except:
                raise ValueError("Could not parse input datetime object.")
        

        
        # Assume lat/lon are fine. They are just sent as floats anyway.
        latitude = float(latitude)
        longitude = float(longitude)

        # Altitude - clip to 0-65535
        altitude = int(altitude)
        if altitude < 0:
            altitude = 0
        elif altitude > 65535:
            altitude = 65535
        
        # Ground Speed - clip to 0-255 (kph)
        speed = int(speed)
        if speed < 0:
            speed = 0
        elif speed > 255:
            speed = 255

        # Satellites - clip to 0-255
        satellites = int(satellites)
        if satellites < 0:
            satellites = 0
        elif satellites > 255:
            satellites = 255
        
        # Temperature - clip to -128 to 127
        temperature = int(temperature)
        if temperature < -128:
            temperature = -128
        elif temperature > 127:
            temperature = 127

        # Battery voltage clip and conversion
        battery_voltage = float(battery_voltage)
        if battery_voltage > 5.0:
            battery_voltage = 5.0
        elif battery_voltage < 0.0:
            battery_voltage = 0.0
        battery_voltage = int(255 * battery_voltage/5.0)

        ## Default Custom Field data

        # Ascent rate is in the range -327.68 to 327.67 m/s
        ascent_rate_100 = int(ascent_rate*100)
        if ascent_rate_100 < -32768:
            ascent_rate_100 = 32768
        elif ascent_rate_100 > 32767:
            ascent_rate_100 = 32767

        # PTU data
        # External Temperature, in the range -3276.8 to 3276.7
        ext_temperature_10 = int(ext_temperature*10)
        if ext_temperature_10 < -32768:
            ext_temperature_10 = -32768
        elif ext_temperature_10 > 32767:
            ext_temperature_10 = 32767

        # Humidity - Integer in range 0-255
        ext_humidity = int(ext_humidity)
        if ext_humidity > 255:
            ext_humidity = 255
        elif ext_humidity < 0:
            ext_humidity = 0

        # Pressure, in the range 0-6553.5 hPa
        ext_pressure_10 = int(ext_pressure*10)
        if ext_pressure_10 < 0:
            ext_pressure_10 = 0
        elif ext_pressure_10 > 65535:
            ext_pressure_10 = 65535
        
        # Encode the default custom field segment
        custom_bytes = struct.pack("<hhBHxx", ascent_rate_100, ext_temperature_10, ext_humidity, ext_pressure_10)

        # Custom data Override, if provided
        if custom_data is not None:
            if type(custom_data) == bytes and len(custom_data) == 9:
                custom_bytes = custom_data

        # Generate the packet, without CRC

        packet_bytes = add_packet_crc(struct.pack(
            '<HHBBBffHBBbB9s',
            payload_id,
            sequence_number,
            hours,
            minutes,
            seconds,
            latitude,
            longitude,
            altitude,
            speed,
            satellites,
            temperature,
            battery_voltage,
            custom_bytes
        ))

        if return_uncoded:
            return packet_bytes
        else:
            (_coded, _) = self.horus_l2_encode_packet(packet_bytes)
            return _coded


class HorusEncoderTests(unittest.TestCase):        
    def test_encoder(self):
        import pprint
        e = Encoder()

        # Check of get_num_tx_data_bytes
        logging.debug(f"Horus v1: 22 bytes in, {e.get_num_tx_data_bytes(22)} bytes out.")
        logging.debug(f"Horus v2: 32 bytes in, {e.get_num_tx_data_bytes(32)} bytes out.")

        logging.debug("Encoder Tests: ")
        horus_v1_unencoded = "000900071E2A000000000000000000000000259A6B14"
        horus_v1_unencoded = "e701010000000000000000000000000000000022020000000000000000006e8e"
        logging.debug(f"  Horus v1 Input:  {horus_v1_unencoded}")
        horus_v1_unencoded_bytes = codecs.decode(horus_v1_unencoded, 'hex')
        (_encoded, _num_bytes) = e.horus_l2_encode_packet(horus_v1_unencoded_bytes)
        logging.debug(f"  Horus v1 Output: {codecs.encode(_encoded, 'hex').decode().upper()}")


        logging.debug("Decoder Tests:")
        horus_v1_encoded = "2424C06B300D0415C5DBD332EFD7C190D7AF7F3C2891DE9F4BA1EB2B437BE1E2D8419D3DC9E44FDF78DAA07A98"
        logging.debug(f"  Horus v1 Input:  {horus_v1_encoded}")
        horus_v1_encoded_bytes = codecs.decode(horus_v1_encoded, 'hex')
        _decoded = e.horus_l2_decode_packet(horus_v1_encoded_bytes, 22)
        logging.debug(f"  Horus v1 Output: {codecs.encode(_decoded, 'hex').decode().upper()}")


        logging.debug("Horus V2 Packet Generator Tests:")
        # Null packet, using all default fields
        horusv2_null = e.create_horus_v2_packet(return_uncoded=True)
        logging.debug(f"Horus V2 Null Packet, Uncoded: {codecs.encode(horusv2_null, 'hex').decode().upper()}")
        horusv2_null_decoded = decode_packet(horusv2_null)
        logging.debug(f"Horus V2 Null Packet, Decoded:")
        logging.debug(pprint.pformat(horusv2_null_decoded))

        horusv2_null = e.create_horus_v2_packet(return_uncoded=False)
        logging.debug(f"Horus V2 Null Packet, Coded: {codecs.encode(horusv2_null, 'hex').decode().upper()}")
        horusv2_null_decoded = decode_packet(e.horus_l2_decode_packet(horusv2_null, 32))
        logging.debug(f"Horus V2 Null Packet, Decoded:")
        logging.debug(pprint.pformat(horusv2_null_decoded))

        logging.debug(f"Horus v2 Null Packet Encoded 4FSK Symbols: {e.bytes_to_4fsk_symbols(horusv2_null)}")
        logging.debug(f"Horus v2 Null Packet Encoded OneBitPerByte: {e.bytes_to_onebitperbyte(horusv2_null)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()