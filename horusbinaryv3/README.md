Payload format information for proposed Horus Binary v3 protocol.
--

Horus Binary v2 currently uses a combination of [custom_field_list.json](https://github.com/projecthorus/horusdemodlib/blob/master/custom_field_list.json) and [payload_id_list.txt](https://github.com/projecthorus/horusdemodlib/blob/master/payload_id_list.txt) to define how packets are decoded. While this keeps the payload size down while still allowing custom it creates a central authority and administrative overhead for managing callsigns and custom field data.

This proposed Horus Binary v3 format intends to address these shortcomings by defining a protocol format that is flexible enough to allow customization while still keeping a small overall size.

To allow this flexibility and to accommodate text descriptions in the callsign and sensor fields the packet size will need to be increased from 32 to 64 for most usages.

### Playground
[Play with the prototype encoder / decoder on our demo page](https://xssfox.github.io/horusbinaryv3/)

### Requirements
- 62 bytes of payload data + 2 bytes of CRC
- Removal of central authority for callsigns / fields
- Able to be encoded on a micro controller / integrate with existing Horus Binary solutions

### Why ASN.1?
Abstract Syntax Notation 1 (ASN.1) is a way to describe data formats. The ASN.1 language lets us define the fields and data types that we expect see in a telemetry packet.

A simplified example of an ASN.1 definition:

```asn1
Telemetry ::= SEQUENCE {
    payloadCallsign     IA5String,
    sequenceNumber      INTEGER,
}
```

ASN.1 defines several encoding rules. These are the rules that define how encoders should take an ASN.1 definition + input data and convert that to an output data format. Some notable examples are BER (Basic Encoding Rules), JER (Json Encoding Rules) and XER (XML Encoding Rules). 

The most interesting for us is UPER - Unaligned Packed Encoding Rules. UPER is interesting for us as it doesn't require word or byte alignment. Many other systems enforce a word or byte alignment due to balancing speed vs space. Additionally unlike BER, UPER does not send tag (or length in some cases) information. This means that both sides of the communication require knowledge of the specification to decode correctly.

Unlike using ctypes and unpacking, ASN.1 allows us to use flexible field such as variable length arrays (SEQUENCE OF) and dynamic types (CHOICE).

The outcome of using ASN.1 and UPER is fairly small packets that can be flexible.

### Expanding
ASN.1 provides a special field called an "extension mark". The extension mark lets us signal to the encoder and decoder that there might be more fields after this point. This allows us to provide an initial first version, then iterate later by adding fields. This extension marker makes the changes both forwards and backwards compatible.

### HorusBinaryV3 Structure and Limitations
This provides a human readable version of the definition. For specifics check the .asn1 file provided.

#### Required Fields
This fields are required to be transmitted/encoded

| Field Name | Constraint | Description |
| -- | -- | -- |
| payloadCallsign | 1 to 15 characters : `a-z`,`A-Z`,`0-9`,`-` | Payload callsign | 
| sequenceNumber | 0 - 65535 | Every transmission this number should increment. It should never go backwards (apart from rollover). It's expected to roll over at 65535 |
| timeOfDaySeconds | -1 - 86400 | This is the time since midnight UTC. If for some reason this is unknown, this should be set to -1 |
| latitude | -9000000 - 9000000 | The payloads current latitude - if this is not known send inf ** These values are *100000 to provide fixed point values ** | 
| longitude | -18000000..18000000 | The payloads current longitude - if this is not known send inf ** These values are *100000 to provide fixed point values ** | 
| altitudeMeters | -1000 - 50000 | If the altitude is not known, transmit -1000 |

**Explanatory notes:** While timeOfDaySeconds, latitude, longitude, altitudeMeters could have been marked as optional in the ASN.1 definition, doing so would cause a bit to be used for each field. Since the majority of payloads will be sending this data making them required allows us to save some space.

#### Built-in Single Value Fields
These fields are optional, and store only a single value.
| Field Name | Constraint | Description |
| -- | -- | -- |
| velocityHorizontalKilometersPerHour | 0-512 | Horizontal velocity in m/s|
| ascentRateCentimetersPerSecond | -32767 - 32767 | Ascent rate in centimeters per second. Centimeters is used here to avoid using a REAL which takes up 2 bytes. |
| gnssSatellitesVisible | 0 - 31 | Number of satellites the payload can see. This figure should not roll over. |
| humidityPercentage | 0 - 100 | Humidity in percentage |
| pressurehPa | 0 - 1200 | Atmospheric pressure in hPa |
| customData | OCTET STRING (aka bytes) | Used to encode binary data. Won't be presented on SondeHub but will be recorded |
| - | - | - |
| gnssPowerSaveState | 0-5 | u-blox GNSS Power Save State |

#### Built-in Multi Value Fields
Each of these fields can have several values. When sending multiple values, ensure that the values remain in order/index. Additional values can use the extraSensors feature.

| Field Name | Sub Field name| Constraint | Description |
| -- | -- | -- | -- |
| temperatureCelsius |  |  |
| -                  | internal | -1023 - 1023 | Sensor temperature in Celsius ** value *10 ** |
| -                  | external | -1023 - 1023 | Sensor temperature in Celsius ** value *10 ** |
| -                  | custom1  | -1023 - 1023 | Sensor temperature in Celsius ** value *10 ** |
| -                  | custom2  | -1023 - 1023 | Sensor temperature in Celsius ** value *10 ** |
| milliVolts | |
| -          | battery | 0 - 16383 | Voltage in milliVolts |
| -          | solar | 0 - 16383 | Voltage in milliVolts |
| -          | custom1 | 0 - 16383 | Voltage in milliVolts |
| -          | custom2 | 0 - 16383 | Voltage in milliVolts |
| counts (max 8) | Integer (unbounded) | Something that needs counting, like a radiation sensor |

#### Custom sensors (extraSensors)
Up to four additional sensor types can be configured. Each additional sensor type can have the following values:
- 4x Integers
- 4x Reals (floating points)
- 1x String `a-z`,`A-Z`,`0-9`,`_ +/=-.`
- 8x Boolean

Custom sensor types should always be sent in order. If no data is available for a type the sensor type should be sent with no sensor values.

This allows for combinations such as:
##### Example 1
- 4x Integers
- 4x Integers
- 4x Integers
- 4x Integers

##### Example 2
- 2x Real
- 4x Integers
- 8x Booleans
- 1x String


##### Structure
Note that while these examples list several fields, the data must also fit within the packet limits.

| Telemetry field | Constraint| Sensor Type | Choice (one of) | Constraint | Description |
| -- | -- | -- | -- | -- | -- |
| `extraSensors[]` | (max 4 items) | name | | `a-z`, `0-9`, `-` |
|              |   | values | `horusStr` | `a-z`,`A-Z`,`0-9`,`_ +/=-.` |
|              |   |  | `horusInt[]` | Integer (max 4 items) |
|              |   |  | `horusReal[]` | Real (max 4 items) | 
|              |   |  | `horusBool[]` | Boolean (max 8 items) | 

##### Example input data for extra sensors
It's sometimes easier to understand as data being encoded.
```python
"extraSensors": [
        {
            "name": "hbk8359", 
            # the list of values allows for multiple of the same sensor
            # a limitation of this is that all of the same type of sensor will need to be sent at once
            # as there would otherwise be no way to index them
            "values": ("horusInt", [1,2]) 
        },
        {
            "name": "crm114",
            "values": ("horusBool", {
                "b0": True,"b1": True,"b2": True,"b3": True,"b4": True,"b5": True,"b6": True,"b7": True
            })
        },
        { # name can be left off to save space
            "values": ("horusInt", [1,2,3])
        },
        {
            "name": "name-only" # just send names if the sequency remains in order
        }
]
```

### Using

Various tools can be used to generate ASN.1 encoding and decoding code. Two used in validation of this project is `asn1tools` for Python and `asn1c` for C.

#### Encoding tips
Care needs to be taken when encoding for transmission. As our available space is only 60 bytes and our packet is variable in size, we need to make sure that our packet isn't too large. We should expect that this happens and handle it accordingly.

One approach:

0. Have a list of high and low priority fields
1. Encode the packet, check if its too long. If it's short enough send it.
2. If it's too long, remove low priority fields until it fits.
3. (Optional) Sort field priority list so another field is removed next time to balance which fields aren't sent.

Tip:
Names of sensors don't need to sent all the time, these can be sent occasionally, or even not at all if default names are ok. 

###  Example Encoding/Decoding Using Python
```python
import asn1tools
uper = asn1tools.compile_files("./HorusBinaryV3.asn1", codec="uper")
data =  {
    "payloadCallsign": "VK3FUR",
    "sequenceNumber": 1234,

    "timeOfDaySeconds": 9001,
    "latitude": 89_94589,
    "longitude": -23_34458,
    "altitudeMeters": 23000,

    "velocityHorizontalKilometersPerHour": 200,
    "gnssSatellitesVisible": 18,

    "temperatureCelsius": {
        "internal": 100,
        "external": 200
    },
    "milliVolts": {
        "battery": 2300
    },

    "ascentRateCentimetersPerSecond": 1080,
    "humidityPercentage": 10,

    "extraSensors": [
        {
            "name": "rad", 
            "values": ("horusInt", [1,2,3])
        }
    ]
}

binary_output_uper = uper.encode('Telemetry', data)
print(f"hex uper: {binary_output_uper.hex()}")
print(f"bytes  uper: {len(binary_output_uper)}")
```
Output:
```
hex uper: 7f7161585460741348465512935d3bc261baee0189c2ce60101010201033225086f918e638a823f0
bytes  uper: 40
```

Decoding:
```python
uper.decode('Telemetry',binary_output_uper)
```

Output:
```
{
  "payloadCallsign": "VK3FUR",
  "sequenceNumber": 1234,
  "timeOfDaySeconds": 9001,
  "latitude": 8994589,
  "longitude": -2334458,

  "altitudeMeters": 23000,
  "extraSensors": [
    {
      "name": "rad",
      "values": [
        "horusInt",
        [
          1,
          2,
          3
        ]
      ]
    }
  ],
  "velocityHorizontalKilometersPerHour": 200,
  "gnssSatellitesVisible": 18,
  "ascentRateCentimetersPerSecond": 1080,
  "temperatureCelsius": {
    "internal": 100,
    "external": 200
  },
  "humidityPercentage": 10,
  "milliVolts": {
    "battery": 2300
  }
}
```

### Encoding with C (asn1c)
Prepare the library
```sh
mkdir horusbinaryc; cd horusbinaryc
asn1c -gen-PER ../HorusBinaryV3.asn1
rm converter-sample.c # We don't need the sample - this will cause a conflict when linking
```
Note - I am not a C developer. This is probably all wrong

```c
#include "Telemetry.h"
#include "AdditionalSensors.h"
#include "AdditionalSensorType.h"
#include "CustomFieldValues.h"

#include <stdio.h>
#include <sys/types.h>

int main (){
    Telemetry_t *packet;
    AdditionalSensors_t *sensors;
    AdditionalSensorType_t *sensor;
    CustomFieldValues_t *customSensorValues;
    IA5String_t *sensorName;
    asn_enc_rval_t ec;

    packet = calloc(1, sizeof(Telemetry_t));
    sensors = calloc(1, sizeof(AdditionalSensors_t));
    sensor = calloc(1, sizeof(AdditionalSensorType_t));
    sensorName = calloc(1, sizeof(IA5String_t));
    customSensorValues = calloc(1, sizeof(CustomFieldValues_t));

    
    if (!packet) {
        perror("calloc failed");
        exit(1);
    } // ideally do this for all the other calloc calls...

    char * callsign = "VK3FUR";

    
    packet->payloadCallsign.size=6;
    packet->payloadCallsign.buf = (uint8_t *)callsign;

    packet->sequenceNumber = 1;
    packet->timeOfDaySeconds=3;
    packet->latitude=23;
    packet->longitude=34;
    packet->altitudeMeters=56;
    
    
    sensorName->buf = (uint8_t *)"meow";
    sensorName->size=4;


    long sensorValue = 123;
    long *sensorValues[1];
    sensorValues[0]=&sensorValue;


    
    customSensorValues->choice.horusInt.list.size = 1;
    customSensorValues->choice.horusInt.list.count = 1;
    customSensorValues->choice.horusInt.list.array=sensorValues;
    customSensorValues->present = CustomFieldValues_PR_horusInt;

    sensor->values = customSensorValues;
    sensor->name = sensorName;
   
    AdditionalSensorType_t *listOfSensors[1];
    listOfSensors[0] = sensor;

    sensors->list.array= listOfSensors;
    sensors->list.size=1;
    sensors->list.count=1;

    packet->extraSensors=sensors;

    
    uint8_t outbuf[300];
    ec = uper_encode_to_buffer(&asn_DEF_Telemetry, packet, outbuf, sizeof(outbuf));
    if(ec.encoded == -1) {
        fprintf(stderr, "Could not encode Packet (at %s)\n"
            ,
            ec.failed_type ? ec.failed_type->name : "unknown"
         );
        exit(1);
    } 

    for(int x=0; x<=ec.encoded;x+=8){
        printf("%02x", outbuf[x/8]);
    }
    printf("\n");
}
```

Compile and run:
```sh
cc -I. *.c -o test
./test
4002c0a8883ee0000800100e00005c0e0004441080c6b9ecc2802f60
```


### SondeHub considerations
 - Should we setup a new horus specific endpoint so only the binary data needs submitting, then decode it on the server side
 - How do we handle the field names only being occasionally sent, maybe we set all the field ids generically then handle the custom names at display time in the SondeHub UI / Grafana?

