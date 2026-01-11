import unittest
import asn1tools
import logging
import json
import datetime

class TestHorusBinaryV3_0(unittest.TestCase):
    def setUp(self):
        self.uper = asn1tools.compile_files("./HorusBinaryV3.asn1", codec="uper")
        self.maxDiff = None

    # This tests building a payload with practically every feature
    def test_bells_and_whistles(self):
        
        data = { # This is an example packet that will be way too big, but it highlights all the features
            "payloadCallsign": "abcDEF-0123abc-",
            "sequenceNumber": 65535,
            "timeOfDaySeconds": 86400,
            "latitude": 9000000,
            "longitude": -18000000,
            "altitudeMeters": 50000,
            "velocityHorizontalKilometersPerHour": 255,
            "gnssSatellitesVisible": 31,
            "ascentRateCentimetersPerSecond": 32767,
            "pressurehPa-x10": 1270,
            "temperatureCelsius-x10": {
                "internal": -127,
                "external": 127,
                "custom1": -127,
                "custom2": 127,
                
            },
            "humidityPercentage":100,
            "milliVolts": {
                "battery": 0,
                "solar": 16383,
                "custom1": 0,
                "custom2": 16383,
                },
            "counts": [1,100,1000,10000,100000,1000000,1000000],
            "gnssPowerSaveState": "tracking",

            "extraSensors": [
                {
                    "name": "hbk8359hbk8359hbk835", 
                    "values": ("horusInt", [1,2]) 
                },
                {
                    "name": "crm114",
                    "values": ("horusBool", {
                        "b0": True,"b1": True,"b2": True,"b3": True,"b4": True,"b5": True,"b6": True,"b7": True
                    })
                },
                { 
                    "values": ("horusStr", "ABCEDFGEFGH123324asdbkjbsdg")
                },
                {
                    "values": ("horusReal",[0.1234,1232342345234234,0.1234,1232342345234234])
                }
            ],
        }
        encoded = self.uper.encode("Telemetry",data)
        decoded = self.uper.decode("Telemetry", encoded)

        logging.debug(f"Length: {len(encoded)} Data: {encoded.hex()}")

        self.assertDictEqual(data, decoded)

    def test_bells_and_whistles_extend(self):
        data = { # This is an example packet that will be way too big, but it highlights all the features
            "payloadCallsign": "abcDEF-0123abc-",
            "sequenceNumber": 65535,
            "timeOfDaySeconds": 86400,
            "latitude": 9000000,
            "longitude": -18000000,
            "altitudeMeters": 50000,
            "velocityHorizontalKilometersPerHour": 255,
            "gnssSatellitesVisible": 31,
            "ascentRateCentimetersPerSecond": 32767,
            "pressurehPa-x10": 1270,
            "temperatureCelsius-x10": {
                "internal": -127,
                "external": 127,
                "custom1": -127,
                "custom2": 127,
                
            },
            "humidityPercentage":100,
            "milliVolts": {
                "battery": 0,
                "solar": 16383,
                "custom1": 0,
                "custom2": 16383,
                },
            "counts": [1,100,1000,10000,100000,1000000,1000000],
            "gnssPowerSaveState": "tracking",

            "extraSensors": [
                {
                    "name": "hbk8359hbk8359hbk835", 
                    "values": ("horusInt", [1,2]) 
                },
                {
                    "name": "crm114",
                    "values": ("horusBool", {
                        "b0": True,"b1": True,"b2": True,"b3": True,"b4": True,"b5": True,"b6": True,"b7": True
                    })
                },
                { 
                    "values": ("horusStr", "ABCEDFGEFGH123324asdbkjbsdg")
                },
                {
                    "values": ("horusReal",[0.1234,1232342345234234,0.1234,1232342345234234])
                }
            ],
        }
        encoded = self.uper.encode("Telemetry",data)
        
        # extend the spec by adding some extra fields to the end
        with open("./HorusBinaryV3.asn1","r") as f:
            horus_def = f.read()
        horus_def = horus_def.replace("...","""
        ...,
        testExtend1 [19] EXPLICIT INTEGER (0..127),
        testExtend2 [20] EXPLICIT IA5String -- MARKER
        """,1)
        extended_uper = asn1tools.compile_string(horus_def, codec="uper")
        decoded = extended_uper.decode("Telemetry", encoded)

        # Test that we can still read old data
        self.assertDictEqual(data, decoded)

        # Test that old encoders can read new data
        extended_data = dict(data)
        extended_data["testExtend1"] = 99
        extended_data["testExtend2"] = "test string"
        extended_encoded = extended_uper.encode("Telemetry",extended_data)
        logging.debug(f"Length: {len(extended_encoded)} Data: {extended_encoded.hex()}")
        extended_decoded = self.uper.decode("Telemetry", extended_encoded)
        self.assertDictEqual(data, extended_decoded)
        
        # Test we can actually decode the new values
        extended_decoded_full = extended_uper.decode("Telemetry", extended_encoded)
        self.assertDictEqual(extended_data, extended_decoded_full)
        

        # Test extending further
        horus_def = horus_def.replace("-- MARKER",""",
        testExtend3 [21] EXPLICIT INTEGER 
        """,1)
        extended_more_uper = asn1tools.compile_string(horus_def, codec="uper")
        decoded_more = extended_more_uper.decode("Telemetry", encoded)

        # Test that we can still read old data
        self.assertDictEqual(data, decoded_more)

        # Test that we can read 2nd revision data
        decoded_more_2 = extended_more_uper.decode("Telemetry", extended_encoded)
        self.assertDictEqual(extended_data, decoded_more_2)

        # Test that the 3rd revision can read the third encoded
        extended_more_data = dict(extended_data)
        extended_more_data["testExtend3"] = 99
        
        extended_more_encoded = extended_more_uper.encode("Telemetry",extended_more_data)
        extended_more_decoded = extended_more_uper.decode("Telemetry",extended_more_encoded)
        self.assertDictEqual(extended_more_data, extended_more_decoded)

        # Test that the 2nd revision encoder can read the third revision data
        extended_more_2_decoded = extended_uper.decode("Telemetry",extended_more_encoded)
        self.assertDictEqual(extended_data, extended_more_2_decoded)


    def test_required_fields_small(self):
        data = { 
            "payloadCallsign": "abcDEF-0123abc-",
            "sequenceNumber": 65535,
            "timeOfDaySeconds": 86400,
            "latitude": 9000000,
            "longitude": -18000000,
            "altitudeMeters": 50000,
        }
        encoded = self.uper.encode("Telemetry",data)
        decoded = self.uper.decode("Telemetry", encoded)

        logging.debug(f"Length: {len(encoded)} Data: {encoded.hex()}")

        self.assertDictEqual(data, decoded)
        self.assertLessEqual(len(data), 30)


    def test_can_decode_known(self):
        # Ensure that we can decode an older packet and nothing has changed. Once spec finialised this value shouldn't need changing
        KNOW_PAYLOAD="7ffe9a7a0f4110020c41669e803fffea30312a88000000031ce3e6918a9220c52462a488314918a9220ca0202020594d71708217ff41b20449142654b142a58b860e2040712adeae58d5a2c7ab98b61301903f2e48e8a71de61300020460cf0fbab73a1301903f2e48e8a71de61300020460cf0fbab73a7ffffff84f6f7011f9c047ec9e0007ffe0007fff804040590080fa0089c400c061a800c3d09000c3d09018436b2b7bbb6b2b7bb8"
        data = { # This is an example packet that will be way too big, but it highlights all the features
            "payloadCallsign": "abcDEF-0123abc-",
            "sequenceNumber": 65535,
            "timeOfDaySeconds": 86400,
            "latitude": 9000000,
            "longitude": -18000000,
            "altitudeMeters": 50000,
            "velocityHorizontalKilometersPerHour": 255,
            "gnssSatellitesVisible": 31,
            "ascentRateCentimetersPerSecond": 32767,
            "pressurehPa-x10": 1270,
            "temperatureCelsius-x10": {
                "internal": -127,
                "external": 127,
                "custom1": -127,
                "custom2": 127,
                
            },
            "humidityPercentage":100,
            "milliVolts": {
                "battery": 0,
                "solar": 16383,
                "custom1": 0,
                "custom2": 16383,
                },
            "counts": [1,100,1000,10000,100000,1000000,1000000],
            "gnssPowerSaveState": "tracking",
            "customData": b"meowmeow",

            "extraSensors": [
                {
                    "name": "hbk8359hbk8359hbk835", 
                    "values": ("horusInt", [1,2]) 
                },
                {
                    "name": "crm114",
                    "values": ("horusBool", {
                        "b0": True,"b1": True,"b2": True,"b3": True,"b4": True,"b5": True,"b6": True,"b7": True
                    })
                },
                { 
                    "values": ("horusStr", "ABCEDFGEFGH123324asdbkjbsdg")
                },
                {
                    "values": ("horusReal",[0.1234,1232342345234234,0.1234,1232342345234234])
                }
            ],
        }
        
        # Check if the we encoded the same
        encoded = self.uper.encode("Telemetry",data).hex()
        self.assertEqual(KNOW_PAYLOAD, encoded)

        decoded = self.uper.decode("Telemetry", bytes.fromhex(KNOW_PAYLOAD))

        self.assertDictEqual(data, decoded)

    # Run through a test horus flight
    def test_itswindy(self):
        with open("./tests/ITSWINDY.json") as f:
            itswindy = json.load(f)
        max_length = 0
        for data in itswindy:
            seconds = (datetime.datetime.fromisoformat(data["datetime"]) - datetime.datetime.fromisoformat(data["datetime"]).replace(hour=0, minute=0, second=0, microsecond=0)).seconds
            to_encode = {
                "payloadCallsign": data['payload_callsign'],
                "sequenceNumber": data['frame'],
                "timeOfDaySeconds": seconds,
                "latitude": int(data['lat']*10_0000),
                "longitude": int(data['lon']*10_0000),
                "altitudeMeters": data['alt'],

                "gnssSatellitesVisible": data['sats'],
                "temperatureCelsius-x10": {
                    "internal": int(data['temp']), 
                    "external": int(data['ext_temperature'])
                },
                "milliVolts": {"battery": int(data['batt']*1000)},
                "humidityPercentage": data['ext_humidity'],
                "ascentRateCentimetersPerSecond": int(data["ascent_rate"]*100),
                "pressurehPa-x10": int(data['ext_pressure'])*10,
                "gnssPowerSaveState": "tracking",
            }
            encoded = self.uper.encode("Telemetry",to_encode)
            if len(encoded) > max_length:
                max_length = len(encoded)
            decoded = self.uper.decode("Telemetry",encoded)

            self.assertEqual(decoded["gnssSatellitesVisible"],data['sats'])
            self.assertEqual(decoded["sequenceNumber"],data['frame'])
            self.assertEqual(decoded["altitudeMeters"],data['alt'])
            self.assertEqual(decoded["timeOfDaySeconds"],seconds)
            self.assertEqual(decoded["payloadCallsign"],data['payload_callsign'])
            self.assertEqual(decoded["latitude"],int(data['lat']*10_0000))
            self.assertEqual(decoded["longitude"],int(data['lon']*10_0000))
            self.assertEqual(decoded["temperatureCelsius-x10"]["internal"],data['temp'])
            self.assertEqual(decoded["ascentRateCentimetersPerSecond"],int(data["ascent_rate"]*100))
            self.assertEqual(decoded["milliVolts"]["battery"],int(data['batt']*1000))
            self.assertEqual(decoded["pressurehPa-x10"],int(data['ext_pressure']*10))
            self.assertLess(len(encoded),48)
            logging.debug(f"Length: {len(encoded)} Data: {encoded.hex()}")
        logging.debug(f"Max length was {max_length}")
        logging.debug(decoded)

if __name__ == "__main__":
    logging.getLogger().setLevel( logging.DEBUG )
    logging.basicConfig(format="%(funcName)s:%(lineno)s %(message)s")
    unittest.main()