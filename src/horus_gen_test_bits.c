/*---------------------------------------------------------------------------*\

  FILE........: horus_gen_tx_bits.c
  AUTHOR......: Mark Jessop
  DATE CREATED: May 2020

  Horus dummy packet generation, for use with fsk_demod.

  Build:
  gcc horus_gen_test_bits.c horus_l2.c golay23.c -o horus_get_test_bits -Wall -DSCRAMBLER -DINTERLEAVER

  \*---------------------------------------------------------------------------*/

#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>
#include <getopt.h>
#include <sys/types.h>

#include "horus_l2.h"
#include "H_128_384_23.h"
#include "H_256_768_22.h"

#include "Telemetry.h"
#include "AdditionalSensors.h"
#include "AdditionalSensorType.h"
#include "CustomFieldValues.h"


// TODO: Move these packet format definitions to somewhere common.

/* Horus Mode 0 (Legacy 22-byte) Binary Packet */
struct TBinaryPacket0
{
    uint8_t     PayloadID;
    uint16_t	Counter;
    uint8_t	Hours;
    uint8_t	Minutes;
    uint8_t	Seconds;
    float	Latitude;
    float	Longitude;
    uint16_t  	Altitude;
    uint8_t     Speed;       // Speed in km/hr
    uint8_t     Sats;
    int8_t      Temp;        // Twos Complement Temp value.
    uint8_t     BattVoltage; // 0 = 0.5v, 255 = 2.0V, linear steps in-between.
    uint16_t    Checksum;    // CRC16-CCITT Checksum.
}  __attribute__ ((packed));

/* Horus v2 Mode 1 (32-byte) Binary Packet */
struct TBinaryPacket1
{
    uint16_t     PayloadID;
    uint16_t	Counter;
    uint8_t	Hours;
    uint8_t	Minutes;
    uint8_t	Seconds;
    float	Latitude;
    float	Longitude;
    uint16_t  	Altitude;
    uint8_t     Speed;       // Speed in km/hr
    uint8_t     Sats;
    int8_t      Temp;        // Twos Complement Temp value.
    uint8_t     BattVoltage; // 0 = 0.5v, 255 = 2.0V, linear steps in-between.
    uint8_t     dummy1;      // Dummy values for user-configurable section.
    float     dummy2;       // Float 
    uint8_t     dummy3;     // battery voltage test
    uint8_t     dummy4;     // divide by 10
    uint16_t     dummy5;    // divide by 100
    uint16_t    Checksum;    // CRC16-CCITT Checksum.
}  __attribute__ ((packed));

/* Horus v2 Mode 2 (16-byte) Binary Packet (Not currently used) */
struct TBinaryPacket2
{
    uint8_t     PayloadID;
    uint8_t	Counter;
    uint16_t	BiSeconds;
    uint8_t	  LatitudeMSB;
    uint16_t	Latitude;
    uint8_t	  LongitudeMSB;
    uint16_t	Longitude;
    uint16_t  	Altitude;
    uint8_t     BattVoltage; // 0 = 0.5v, 255 = 2.0V, linear steps in-between.
    uint8_t     flags;      // Dummy values for user-configurable section.
    uint16_t    Checksum;    // CRC16-CCITT Checksum.
}  __attribute__ ((packed));




int main(int argc,char *argv[]) {
    int i, framecnt;
    int horus_mode = 0;

    char usage[] = "usage: %s horus_mode numFrames\nMode 0 = Legacy 22-byte Golay FEC\nMode 1 = 32-byte Golay FEC\nMode 2 = 32 byte Horus V3\n";

    if (argc < 3) {
        fprintf(stderr, usage, argv[0]);
        exit(1);
    }

    horus_mode = atoi(argv[1]);
    fprintf(stderr, "Using Horus Mode %d.\n", horus_mode);

    framecnt = atoi(argv[2]);
    fprintf(stderr, "Generating %d frames.\n", framecnt);

    if(horus_mode == 0){
      int nbytes = sizeof(struct TBinaryPacket0);
      struct TBinaryPacket0 input_payload;
      int num_tx_data_bytes = horus_l2_get_num_tx_data_bytes(nbytes);
      unsigned char tx[num_tx_data_bytes];

      uint16_t counter = 0;

      /* all zeros is nastiest sequence for demod before scrambling */
      while(framecnt > 0){
        memset(&input_payload, 0, nbytes);
        input_payload.Counter = counter;
        input_payload.Checksum = horus_l2_gen_crc16((unsigned char*)&input_payload, nbytes-2);

        horus_l2_encode_tx_packet(tx, (unsigned char*)&input_payload, nbytes);

        int b;
        uint8_t tx_bit;
          for(i=0; i<num_tx_data_bytes; i++) {
              for(b=0; b<8; b++) {
                  tx_bit = (tx[i] >> (7-b)) & 0x1; /* msb first */
                  fwrite(&tx_bit,sizeof(uint8_t),1,stdout);
                  fflush(stdout);
              }
          }
          framecnt -= 1;
          counter += 1;
      }

    } else if(horus_mode == 1){
      int nbytes = sizeof(struct TBinaryPacket1);
      struct TBinaryPacket1 input_payload;
      int num_tx_data_bytes = horus_l2_get_num_tx_data_bytes(nbytes);
      unsigned char tx[num_tx_data_bytes];

      uint16_t counter = 0;

      /* all zeros is nastiest sequence for demod before scrambling */
      while(framecnt > 0){
        memset(&input_payload, 0, nbytes);
        input_payload.PayloadID = 256;
        input_payload.Hours = 12;
        input_payload.Minutes = 34;
        input_payload.Seconds = 56;
        input_payload.dummy1 = 1;
        input_payload.dummy2 = 1.23456789;
        input_payload.dummy3 = 200;
        input_payload.dummy4 = 123;
        input_payload.dummy5 = 1234;
        input_payload.Counter = counter;
        input_payload.Checksum = horus_l2_gen_crc16((unsigned char*)&input_payload, nbytes-2);

        horus_l2_encode_tx_packet(tx, (unsigned char*)&input_payload, nbytes);

        int b;
        uint8_t tx_bit;
          for(i=0; i<num_tx_data_bytes; i++) {
              for(b=0; b<8; b++) {
                  tx_bit = (tx[i] >> (7-b)) & 0x1; /* msb first */
                  fwrite(&tx_bit,sizeof(uint8_t),1,stdout);
                  fflush(stdout);
              }
          }
          framecnt -= 1;
          counter += 1;
      } 
    // Leaving this in place unless we ever decide to do an LDPC mode.
    // } else if(horus_mode == 2){
    //   // 16-Byte LDPC Encoded mode.
    //   int nbytes = sizeof(struct TBinaryPacket2);
    //   struct TBinaryPacket2 input_payload;

    //   // TODO: Add Calculation of expected number of TX bytes based on LDPC code.
    //   int num_tx_data_bytes = 4 + H_128_384_23_DATA_BYTES + H_128_384_23_PARITY_BYTES;
    //   unsigned char tx[num_tx_data_bytes];

    //   /* all zeros is nastiest sequence for demod before scrambling */
    //   memset(&input_payload, 0, nbytes);
    //   input_payload.Checksum = horus_l2_gen_crc16((unsigned char*)&input_payload, nbytes-2);


    //   int ldpc_tx_bytes = ldpc_encode_packet(tx, (unsigned char*)&input_payload, 2);

    //   int b;
    //   uint8_t tx_bit;
    //   while(framecnt > 0){
    //       for(i=0; i<num_tx_data_bytes; i++) {
    //           for(b=0; b<8; b++) {
    //               tx_bit = (tx[i] >> (7-b)) & 0x1; /* msb first */
    //               fwrite(&tx_bit,sizeof(uint8_t),1,stdout);
    //               fflush(stdout);
    //           }
    //       }
    //       framecnt -= 1;
    //   }
    } else if (horus_mode == 2) {
      asn_enc_rval_t ec;
      Telemetry_t *packet;
      char * callsign = "4FSKTEST-V2";
      packet = calloc(1, sizeof(Telemetry_t));

      packet->payloadCallsign.size=11;
      
      packet->payloadCallsign.buf = (uint8_t *)callsign;

      packet->sequenceNumber = 1;
      packet->timeOfDaySeconds=3;
      packet->latitude=23;
      packet->longitude=34;
      packet->altitudeMeters=56;

      uint8_t outbuf[30];


      unsigned char payload[32] ={ 
        0x00, 0x00, // crc
      };
      
      int num_tx_data_bytes = horus_l2_get_num_tx_data_bytes(sizeof(payload));
      unsigned char tx[num_tx_data_bytes];
      uint16_t * checksum = (uint16_t *)payload;
      
      uint16_t counter = 0;

      /* all zeros is nastiest sequence for demod before scrambling */
      while(framecnt > 0){
        packet->sequenceNumber = counter;
        ec = uper_encode_to_buffer(&asn_DEF_Telemetry,NULL, packet, outbuf, sizeof(outbuf));
        if(ec.encoded == -1) {
            fprintf(stderr, "Could not encode Packet (at %s)\n"
                ,
                ec.failed_type ? ec.failed_type->name : "unknown"
            );
            exit(1);
        }
        
        memcpy(payload+2,outbuf,30);
        *checksum = horus_l2_gen_crc16(payload+2, sizeof(payload)-2);
        horus_l2_encode_tx_packet(tx, payload, sizeof(payload));

        int b;
        uint8_t tx_bit;
          for(i=0; i<num_tx_data_bytes; i++) {
              for(b=0; b<8; b++) {
                  tx_bit = (tx[i] >> (7-b)) & 0x1; /* msb first */
                  fwrite(&tx_bit,sizeof(uint8_t),1,stdout);
                  fflush(stdout);
              }
          }
          framecnt -= 1;
          counter += 1;
      }
    } else if (horus_mode == 3) {
      asn_enc_rval_t ec;
      Telemetry_t *packet;
      AdditionalSensors_t *sensors;
      AdditionalSensorType_t *sensor;
      CustomFieldValues_t *customSensorValues;
      IA5String_t *sensorName;

      char * callsign = "4FSKTEST-V2";
      
      packet = calloc(1, sizeof(Telemetry_t));
      sensors = calloc(1, sizeof(AdditionalSensors_t));
      sensor = calloc(1, sizeof(AdditionalSensorType_t));
      sensorName = calloc(1, sizeof(IA5String_t));
      customSensorValues = calloc(1, sizeof(CustomFieldValues_t));

      packet->payloadCallsign.size=11;
      
      packet->payloadCallsign.buf = (uint8_t *)callsign;

      packet->sequenceNumber = 1;
      packet->timeOfDaySeconds=3;
      packet->latitude=23;
      packet->longitude=34;
      packet->altitudeMeters=56;

      packet->payloadCallsign.buf = (uint8_t *)callsign;

      packet->sequenceNumber = 1;
      packet->timeOfDaySeconds=3;
      packet->latitude=23;
      packet->longitude=34;
      packet->altitudeMeters=56;
      
      
      sensorName->buf = (uint8_t *)"meowmeow";
      sensorName->size=8;


      long sensorValue = 123;
      long *sensorValues[4];
      sensorValues[0]=&sensorValue;
      sensorValues[1]=&sensorValue;
      sensorValues[2]=&sensorValue;
      sensorValues[3]=&sensorValue;


      
      customSensorValues->choice.horusInt.list.size = 1;
      customSensorValues->choice.horusInt.list.count = 1;
      customSensorValues->choice.horusInt.list.array=sensorValues;
      customSensorValues->present = CustomFieldValues_PR_horusInt;

      sensor->values = customSensorValues;
      sensor->name = sensorName;
    
      AdditionalSensorType_t *listOfSensors[4];
      listOfSensors[0] = sensor;
      listOfSensors[1] = sensor;
      listOfSensors[2] = sensor;
      listOfSensors[3] = sensor;

      sensors->list.array= listOfSensors;
      sensors->list.size=4;
      sensors->list.count=4;

      packet->extraSensors=sensors;


      uint8_t outbuf[62];


      unsigned char payload[64] ={ 
        0x00, 0x00, // crc
      };
      
      int num_tx_data_bytes = horus_l2_get_num_tx_data_bytes(sizeof(payload));
      unsigned char tx[num_tx_data_bytes];
      uint16_t * checksum = (uint16_t *)payload;
      
      uint16_t counter = 0;

      /* all zeros is nastiest sequence for demod before scrambling */
      while(framecnt > 0){
        packet->sequenceNumber = counter;
        ec = uper_encode_to_buffer(&asn_DEF_Telemetry,NULL, packet, outbuf, sizeof(outbuf));
        if(ec.encoded == -1) {
            fprintf(stderr, "Could not encode Packet (at %s)\n"
                ,
                ec.failed_type ? ec.failed_type->name : "unknown"
            );
            exit(1);
        }
        
        memcpy(payload+2,outbuf,62);
        *checksum = horus_l2_gen_crc16(payload+2, sizeof(payload)-2);
        horus_l2_encode_tx_packet(tx, payload, sizeof(payload));

        int b;
        uint8_t tx_bit;
          for(i=0; i<num_tx_data_bytes; i++) {
              for(b=0; b<8; b++) {
                  tx_bit = (tx[i] >> (7-b)) & 0x1; /* msb first */
                  fwrite(&tx_bit,sizeof(uint8_t),1,stdout);
                  fflush(stdout);
              }
          }
          framecnt -= 1;
          counter += 1;
      }
} else if (horus_mode == 4) {
      asn_enc_rval_t ec;
      Telemetry_t *packet;
      AdditionalSensors_t *sensors;
      AdditionalSensorType_t *sensor;
      CustomFieldValues_t *customSensorValues;
      IA5String_t *sensorName;
      OCTET_STRING_t *customData;

      char * callsign = "4FSKTEST-V2";
      
      packet = calloc(1, sizeof(Telemetry_t));
      sensors = calloc(1, sizeof(AdditionalSensors_t));
      sensor = calloc(1, sizeof(AdditionalSensorType_t));
      sensorName = calloc(1, sizeof(IA5String_t));
      customData = calloc(1,sizeof(OCTET_STRING_t));
      customSensorValues = calloc(1, sizeof(CustomFieldValues_t));

      packet->payloadCallsign.size=11;
      
      packet->payloadCallsign.buf = (uint8_t *)callsign;

      packet->sequenceNumber = 1;
      packet->timeOfDaySeconds=3;
      packet->latitude=23;
      packet->longitude=34;
      packet->altitudeMeters=56;

      packet->payloadCallsign.buf = (uint8_t *)callsign;

      packet->sequenceNumber = 1;
      packet->timeOfDaySeconds=3;
      packet->latitude=23;
      packet->longitude=34;
      packet->altitudeMeters=56;
      
      
      sensorName->buf = (uint8_t *)"meowmeow";
      sensorName->size=8;


      long sensorValue = 123;
      long *sensorValues[4];
      sensorValues[0]=&sensorValue;
      sensorValues[1]=&sensorValue;
      sensorValues[2]=&sensorValue;
      sensorValues[3]=&sensorValue;


      
      customSensorValues->choice.horusInt.list.size = 1;
      customSensorValues->choice.horusInt.list.count = 1;
      customSensorValues->choice.horusInt.list.array=sensorValues;
      customSensorValues->present = CustomFieldValues_PR_horusInt;

      sensor->values = customSensorValues;
      sensor->name = sensorName;
    
      AdditionalSensorType_t *listOfSensors[4];
      listOfSensors[0] = sensor;
      listOfSensors[1] = sensor;
      listOfSensors[2] = sensor;
      listOfSensors[3] = sensor;

      sensors->list.array= listOfSensors;
      sensors->list.size=4;
      sensors->list.count=4;

      packet->extraSensors=sensors;

      char * cdata ="WOOFWOOFWOOFWOOFWOOFWOOFWOOFWOOF";

      customData->buf =  (uint8_t *)cdata;
      customData->size = 32;
      packet->customData = customData;


      uint8_t outbuf[126];


      unsigned char payload[128] ={ 
        0x00, 0x00, // crc
      };
      
      int num_tx_data_bytes = horus_l2_get_num_tx_data_bytes(sizeof(payload));
      unsigned char tx[num_tx_data_bytes];
      uint16_t * checksum = (uint16_t *)payload;
      
      uint16_t counter = 0;

      /* all zeros is nastiest sequence for demod before scrambling */
      while(framecnt > 0){
        packet->sequenceNumber = counter;
        ec = uper_encode_to_buffer(&asn_DEF_Telemetry,NULL, packet, outbuf, sizeof(outbuf));
        if(ec.encoded == -1) {
            fprintf(stderr, "Could not encode Packet (at %s)\n"
                ,
                ec.failed_type ? ec.failed_type->name : "unknown"
            );
            exit(1);
        }
        
        memcpy(payload+2,outbuf,126);
        *checksum = horus_l2_gen_crc16(payload+2, sizeof(payload)-2);
        horus_l2_encode_tx_packet(tx, payload, sizeof(payload));

        int b;
        uint8_t tx_bit;
          for(i=0; i<num_tx_data_bytes; i++) {
              for(b=0; b<8; b++) {
                  tx_bit = (tx[i] >> (7-b)) & 0x1; /* msb first */
                  fwrite(&tx_bit,sizeof(uint8_t),1,stdout);
                  fflush(stdout);
              }
          }
          framecnt -= 1;
          counter += 1;
      }
    } else {
      fprintf(stderr, "Unknown Mode!");
    }

    return 0;
}