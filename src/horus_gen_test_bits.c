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

#include "horus_l2.h"
#include "H_128_384_23.h"
#include "H_256_768_22.h"

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
    uint8_t     Speed;       // Speed in Knots (1-255 knots)
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
    uint8_t     Speed;       // Speed in Knots (1-255 knots)
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

    char usage[] = "usage: %s horus_mode numFrames\nMode 0 = Legacy 22-byte Golay FEC\nMode 1 = 32-byte Golay FEC\n";

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
      unsigned char payload[32] ={ // generated from https://xssfox.github.io/horusbinaryv3/ for the time being
        0x00, 0x00, // crc
        0x30, 0x05, 0x85, 0x61,   0x51, 0x81, 0xd0, 0x4d, 
        0x21, 0x19, 0x54, 0x4a,   0x4d, 0x74, 0xef, 0x09,
        0x86, 0x5d, 0xc0, 0x32,   0x24, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,   0x00, 0x00
      };
      int num_tx_data_bytes = horus_l2_get_num_tx_data_bytes(sizeof(payload));
      unsigned char tx[num_tx_data_bytes];
      uint16_t * checksum = (uint16_t *)payload;
      *checksum = horus_l2_gen_crc16(payload+2, sizeof(payload)-2);
      uint16_t counter = 0;

      /* all zeros is nastiest sequence for demod before scrambling */
      while(framecnt > 0){
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
    } else if (horus_mode == 3) { // horus binary v3 64 byte packet
      unsigned char payload[] ={ // generated from https://xssfox.github.io/horusbinaryv3/ for the time being
        0x00, 0x00, // crc
        0x7b, 0xa5, 0x85, 0x61,  0x51, 0x81, 0xd0, 0x4d,
        0x21, 0x19, 0x54, 0x4a,  0x4d, 0x74, 0xef, 0x09, 
        0x86, 0x5d, 0xc0, 0x31,  0x38, 0x59, 0xcc, 0x02, 
        0x02, 0x02, 0x04, 0x02,  0x06, 0x64, 0x4a, 0x10, 
        0xdf, 0x23, 0x1c, 0xc7,  0x15, 0x04, 0x7e, 0x30,
        0x55, 0x55, 0x55, 0x55,  0x55, 0x55, 0x55, 0x55, 
        0x55, 0x55, 0x55, 0x55,  0x00, 0x55, 0x55, 0x55,
        0x55, 0x55, 0x55, 0x55,  0x00, 0x00
      };
      int num_tx_data_bytes = horus_l2_get_num_tx_data_bytes(sizeof(payload));
      unsigned char tx[num_tx_data_bytes];

      uint16_t counter = 0;

      /* all zeros is nastiest sequence for demod before scrambling */
      while(framecnt > 0){
        payload[63] = counter;
        uint16_t * checksum = (uint16_t *)payload;
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
} else if (horus_mode == 4) { // horus binary v3 128 byte packet
      unsigned char payload[] ={ // generated from https://xssfox.github.io/horusbinaryv3/ for the time being
        0x00, 0x00, // crc
        0x7f,0xe0,0x9f,0xff,0xfe,0xa3,0x03,0x12, 
        0xa8,0x80,0x00,0x00,0x00,0x31,0xce,0x3c,
        0x05,0xa8,0x08,0x08,0x08,0x16,0x02,0xff,
        0xf4,0x01,0x56,0xc0,0x4c,0x06,0x40,0xfc,
        0xb9,0x23,0xa2,0x9c,0x77,0x99,0xff,0xff,
        0xff,0xe0,0xff,0xee,0x02,0x3f,0x38,0x08,
        0xfd,0x93,0xc0,0x00,0xff,0xfc,0x00,0x0f,
        0xff,0xc8,0x08,0x08,0x0b,0x23
      };
      int num_tx_data_bytes = horus_l2_get_num_tx_data_bytes(sizeof(payload));
      unsigned char tx[num_tx_data_bytes];

      uint16_t counter = 0;

      /* all zeros is nastiest sequence for demod before scrambling */
      while(framecnt > 0){
        uint16_t * checksum = (uint16_t *)payload;
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