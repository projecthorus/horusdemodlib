/*---------------------------------------------------------------------------*\

  FILE........: horus_api.c
  AUTHOR......: David Rowe
  DATE CREATED: March 2018

  Library of API functions that implement High Altitude Balloon (HAB)
  telemetry modems and protocols for Project Horus.  May also be useful for
  other HAB projects.

\*---------------------------------------------------------------------------*/

/*
  Copyright (C) 2018 David Rowe

  All rights reserved.

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU Lesser General Public License version 2.1, as
  published by the Free Software Foundation.  This program is
  distributed in the hope that it will be useful, but WITHOUT ANY
  WARRANTY; without even the implied warranty of MERCHANTABILITY or
  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
  License for more details.

  You should have received a copy of the GNU Lesser General Public License
  along with this program; if not, see <http://www.gnu.org/licenses/>.
*/

#include <assert.h>
#include <stdlib.h>
#include <stdio.h>

#include "horus_api.h"
#include "fsk.h"
#include "horus_l2.h"

struct horus ;

int horus_v3_check_sizes[] = {32,48,64,96,128};
/*
RTTY Unique word = $ characters, repeated at least 2 times.
$ = (0)010 0100
Reversed = 0010010(0)
*/
int8_t uw_horus_rtty_7N1[] = {
  0,0,1,0,0,1,0,1,0,
  0,0,1,0,0,1,0,1,0,
};
int8_t uw_horus_rtty_7N2[] = {
  0,0,1,0,0,1,0,1,1,0,
  0,0,1,0,0,1,0,1,1,0,
};
int8_t uw_horus_rtty_8N2[] = {
  0,0,1,0,0,1,0,0,1,1,0,
  0,0,1,0,0,1,0,0,1,1,0,
};

/* Unique word for Horus Binary V1 / V2 */

int8_t uw_horus_binary_v1[] = {
    0,0,1,0,0,1,0,0,
    0,0,1,0,0,1,0,0 
};


// Old LDPC-mode stuff.
// /* Unique word for Horus Binary V2 128/256 bit modes (Last row in the 32x32 Hadamard matrix) */

// int8_t uw_horus_binary_v2[] = {
//     1, 0, 0, 1, 0, 1, 1, 0,  // 0x96
//     0, 1, 1, 0, 1, 0, 0, 1,  // 0x69
//     0, 1, 1, 0, 1, 0, 0, 1,  // 0x69
//     1, 0, 0, 1, 0, 1, 1, 0   // 0x96
// };



struct horus *horus_open (int mode) {
    assert((mode == HORUS_MODE_RTTY_7N1) || (mode == HORUS_MODE_RTTY_7N2) || (mode == HORUS_MODE_RTTY_8N2) || (mode == HORUS_MODE_BINARY_V1) );  //|| (mode == HORUS_MODE_BINARY_V2_256BIT) || (mode == HORUS_MODE_BINARY_V2_128BIT));

    if (mode == HORUS_MODE_RTTY_7N1){
        // RTTY Mode defaults - 100 baud, no assumptions about tone spacing.
        return horus_open_advanced(HORUS_MODE_RTTY_7N1, HORUS_RTTY_DEFAULT_BAUD, -1);
    }
    if (mode == HORUS_MODE_RTTY_7N2){
        // RTTY Mode defaults - 100 baud, no assumptions about tone spacing.
        return horus_open_advanced(HORUS_MODE_RTTY_7N2, HORUS_RTTY_DEFAULT_BAUD, -1);
    } 
    if (mode == HORUS_MODE_RTTY_8N2){
        // RTTY Mode defaults - 100 baud, no assumptions about tone spacing.
        return horus_open_advanced(HORUS_MODE_RTTY_8N2, HORUS_RTTY_DEFAULT_BAUD, -1);
    }
    
    return horus_open_advanced(HORUS_MODE_BINARY_V1, HORUS_BINARY_V1_DEFAULT_BAUD, -1);
}

struct horus *horus_open_advanced (int mode, int Rs, int tx_tone_spacing) {
    return horus_open_advanced_sample_rate(mode, Rs, tx_tone_spacing, 48000, FSK_DEFAULT_P);
}

struct horus *horus_open_advanced_sample_rate (int mode, int Rs, int tx_tone_spacing, int Fs, int P) {
    unsigned long i, mask;
    assert((mode == HORUS_MODE_RTTY_7N1) || (mode == HORUS_MODE_RTTY_7N2) || (mode == HORUS_MODE_RTTY_8N2) || (mode == HORUS_MODE_BINARY_V1) );// || (mode == HORUS_MODE_BINARY_V2_256BIT) || (mode == HORUS_MODE_BINARY_V2_128BIT));

    struct horus *hstates = (struct horus *)malloc(sizeof(struct horus));
    assert(hstates != NULL);

    hstates->Fs = Fs; hstates->Rs = Rs; hstates->verbose = 0; hstates->mode = mode;
    hstates->uw_count = 0;

    if (mode == HORUS_MODE_RTTY_7N1) {
        // Parameter setup for RTTY 7N2 Reception

        hstates->mFSK = 2;
        hstates->max_packet_len = HORUS_RTTY_7N1_NUM_BITS;

        // If baud rate not provided, use default
        if (hstates->Rs == -1){
            hstates->Rs = HORUS_RTTY_DEFAULT_BAUD;
        }

        if (tx_tone_spacing == -1){
            // No tone spacing provided. Use dummy value to keep fsk modem happy, and disable mask estimation.
            tx_tone_spacing = 2*hstates->Rs;
            mask = 0;
        } else {
            mask = 1;
        }

        /* map UW to make it easier to search for */

        for (i=0; i<sizeof(uw_horus_rtty_7N1); i++) {
            hstates->uw[i] = 2*uw_horus_rtty_7N1[i] - 1;
        }        
        hstates->uw_len = sizeof(uw_horus_rtty_7N1);
        hstates->uw_thresh = sizeof(uw_horus_rtty_7N1) - 2;  /* allow a few bit errors in UW detection */
        hstates->rx_bits_len = hstates->max_packet_len;
    }

    if (mode == HORUS_MODE_RTTY_7N2) {
        // Parameter setup for RTTY 7N2 Reception

        hstates->mFSK = 2;
        hstates->max_packet_len = HORUS_RTTY_7N2_NUM_BITS;

        // If baud rate not provided, use default
        if (hstates->Rs == -1){
            hstates->Rs = HORUS_RTTY_DEFAULT_BAUD;
        }

        if (tx_tone_spacing == -1){
            // No tone spacing provided. Use dummy value to keep fsk modem happy, and disable mask estimation.
            tx_tone_spacing = 2*hstates->Rs;
            mask = 0;
        } else {
            mask = 1;
        }

        /* map UW to make it easier to search for */

        for (i=0; i<sizeof(uw_horus_rtty_7N2); i++) {
            hstates->uw[i] = 2*uw_horus_rtty_7N2[i] - 1;
        }        
        hstates->uw_len = sizeof(uw_horus_rtty_7N2);
        hstates->uw_thresh = sizeof(uw_horus_rtty_7N2) - 2;  /* allow a few bit errors in UW detection */
        hstates->rx_bits_len = hstates->max_packet_len;
    }

    if (mode == HORUS_MODE_RTTY_8N2) {
        // Parameter setup for RTTY 8N2 Reception

        hstates->mFSK = 2;
        hstates->max_packet_len = HORUS_RTTY_8N2_NUM_BITS;

        // If baud rate not provided, use default
        if (hstates->Rs == -1){
            hstates->Rs = HORUS_RTTY_DEFAULT_BAUD;
        }

        if (tx_tone_spacing == -1){
            // No tone spacing provided. Use dummy value to keep fsk modem happy, and disable mask estimation.
            tx_tone_spacing = 2*hstates->Rs;
            mask = 0;
        } else {
            mask = 1;
        }

        /* map UW to make it easier to search for */

        for (i=0; i<sizeof(uw_horus_rtty_8N2); i++) {
            hstates->uw[i] = 2*uw_horus_rtty_8N2[i] - 1;
        }        
        hstates->uw_len = sizeof(uw_horus_rtty_8N2);
        hstates->uw_thresh = sizeof(uw_horus_rtty_8N2) - 2;  /* allow a few bit errors in UW detection */
        hstates->rx_bits_len = hstates->max_packet_len;
    }

    if (mode == HORUS_MODE_BINARY_V1) {
        // Parameter setup for the Legacy Horus Binary Mode (22 byte frames, Golay encoding)

        hstates->mFSK = 4;
        hstates->max_packet_len = HORUS_BINARY_V1V2_MAX_BITS;// HORUS_BINARY_V1_NUM_CODED_BITS;

        // If baud rate not provided, use default
        if (hstates->Rs == -1){
            hstates->Rs = HORUS_BINARY_V1_DEFAULT_BAUD;
        }

        if (tx_tone_spacing == -1){
            // No tone spacing provided. Disable mask estimation, and use the default tone spacing value as a dummy value.
            tx_tone_spacing = HORUS_BINARY_V1_DEFAULT_TONE_SPACING;
            mask = 0;
        } else {
            // Tone spacing provided, enable mask estimation.
            mask = 1;
        }

        for (i=0; i<sizeof(uw_horus_binary_v1); i++) {
            hstates->uw[i] = 2*uw_horus_binary_v1[i] - 1;
        }
        hstates->uw_len = sizeof(uw_horus_binary_v1);
        hstates->uw_thresh = sizeof(uw_horus_binary_v1) - 2; /* allow a few bit errors in UW detection */
        horus_l2_init();
        hstates->rx_bits_len = hstates->max_packet_len;
    }

    // Create the FSK modedm struct. Note that the low-tone-frequency parameter is unused.
    #define UNUSED 1000
    hstates->fsk = fsk_create_hbr(hstates->Fs, hstates->Rs, hstates->mFSK, P, FSK_DEFAULT_NSYM, UNUSED, tx_tone_spacing);

    // Set/disable the mask estimator depending on if tx_tone_spacing was provided (refer above)
    fsk_set_freq_est_alg(hstates->fsk, mask);

    /* allocate enough room for two packets so we know there will be
       one complete packet if we find a UW at start */
    
    hstates->rx_bits_len += hstates->fsk->Nbits;
    hstates->rx_bits = (uint8_t*)malloc(hstates->rx_bits_len);
    assert(hstates->rx_bits != NULL);
    for(int i=0; i<hstates->rx_bits_len; i++) {
        hstates->rx_bits[i] = 0;
    }

    // and the same for soft-bits
    hstates->soft_bits = (float*)malloc(sizeof(float) * hstates->rx_bits_len);
    assert(hstates->soft_bits != NULL);
    for(int i=0; i<hstates->rx_bits_len; i++) {
        hstates->soft_bits[i] = 0.0;
    }

    hstates->crc_ok = 0;
    hstates->total_payload_bits = 0;
    
    return hstates;
}

void horus_close (struct horus *hstates) {
    assert(hstates != NULL);
    fsk_destroy(hstates->fsk);
    free(hstates->rx_bits);
    free(hstates);
}

uint32_t horus_nin(struct horus *hstates) {
    assert(hstates != NULL);
    int nin = fsk_nin(hstates->fsk);
    assert(nin <= horus_get_max_demod_in(hstates));
    return nin;
}

void horus_find_uw(struct horus *hstates) {
    int i, j, corr;
    int n = hstates->fsk->Nbits+(hstates->uw_len);
    int rx_bits_mapped[n+hstates->uw_len];
    
    /* map rx_bits to +/-1 for UW search */

    for(i=0; i<n; i++) {
        rx_bits_mapped[i] = 2*hstates->rx_bits[hstates->rx_bits_len-n+i] - 1;
    }
    
    /* look for UW  */

    for(i=0; i<n-hstates->uw_len; i++) {

        /* calculate correlation between bit stream and UW */
        
        corr = 0;
        for(j=0; j<hstates->uw_len; j++) {
            corr += rx_bits_mapped[i+j]*hstates->uw[j];
        }
        
        /* peak pick maximum */
        
        if (corr >= hstates->uw_thresh && hstates->uw_count < MAX_UW_TO_TRACK) {
            int pos = hstates->rx_bits_len-n+i;
            for (int h=0; h< hstates->uw_count;h++){
                if (hstates->uw_loc[h] == pos){
                    if (hstates->verbose) {
                        fprintf(stderr, "uw: already in %d\n",  hstates->uw_loc[h]);
                    }
                    continue;
                }
            }
            hstates->uw_loc[hstates->uw_count] = pos;
            
            if (hstates->verbose) {
                fprintf(stderr, "uw: %d:%d\n", hstates->uw_count, hstates->uw_loc[hstates->uw_count]);
            }
            hstates->uw_count++;
        }
    }

    if (hstates->verbose) {
        fprintf(stderr, "  horus_find_uw: uw_count: %d corr: %d uw_thresh: %d n: %d\n",  hstates->uw_count, corr, hstates->uw_thresh, n);
    }
    

}

int hex2int(char ch) {
    if (ch >= '0' && ch <= '9')
        return ch - '0';
    if (ch >= 'A' && ch <= 'F')
        return ch - 'A' + 10;
    if (ch >= 'a' && ch <= 'f')
        return ch - 'a' + 10;
    return -1;
}


int extract_horus_rtty(struct horus *hstates, char ascii_out[], int uw_loc, int ascii_bits, int stop_bits) {
    const int nfield = ascii_bits;                      /* 7 or 8 bit ASCII                    */
    const int npad   = stop_bits + 1;                   /* N stop bits + start bit between characters */
    int st = uw_loc;                                    /* first bit of first char        */
    int en = st + hstates->max_packet_len - nfield;          /* last bit of max length packet  */

    if (en > hstates->rx_bits_len){
        if (hstates->verbose) {
            fprintf(stderr,"not enough data yet");
        }
        return 0;
    }
    if (hstates->verbose) {
        fprintf(stderr, "st: %d, en: %d %d %d\n", st, en, ascii_bits, stop_bits);
    }

    int      i, j, k, endpacket, nout, crc_ok, rtty_start;
    uint8_t  char_dec;
    char    *pout, *ptx_crc;
    uint16_t rx_crc, tx_crc;

    pout = ascii_out; nout = 0; crc_ok = 0; endpacket = 0; rx_crc = tx_crc = 0;
    
    for (i=st; i<en; i+=nfield+npad) {

        /* assemble char LSB to MSB */

        char_dec = 0;
        for(j=0; j<nfield; j++) {
            assert(hstates->rx_bits[i+j] <= 1);
            char_dec |= hstates->rx_bits[i+j] * (1<<j);
        }
        if (hstates->verbose) {
            fprintf(stderr, "  extract_horus_rtty i: %4d 0x%02x %c \n", i, char_dec, char_dec);
            if ((nout % 6) == 0) {
                fprintf(stderr, "\n");
            }
        }

        /*  if we find a '*' that's the end of the packet for RX CRC calculations */

        if (!endpacket && (char_dec == 42)) {
            endpacket = 1;
            rtty_start = 0;
            // Find the end of the $$s
            for(k = 0; k<8; k++){
                if(ascii_out[k] != 36){
                    rtty_start = k;
                    break;
                }
            }
            if(hstates->verbose){
                fprintf(stderr, "  Found %d $s\n", rtty_start);
            }

            rx_crc = horus_l2_gen_crc16((uint8_t*)&ascii_out[rtty_start], nout-rtty_start);
            ptx_crc = pout + 1; /* start of tx CRC */
            if (hstates->verbose){
                fprintf(stderr, "  begin endpacket\n");
            }
            // Only process up to the next 5 characters (checksum + line ending)
            en = i + (ascii_bits+stop_bits+1)*5;
        }

        /* build up output array, really only need up to tx crc but
           may end up going further */
        
        *pout++ = (char)char_dec;
        nout++;
        
    }

    /* if we found the end of packet flag and have enough chars to compute checksum ... */

    //fprintf(stderr, "\n\ntx CRC...\n");
    if (endpacket && (pout > (ptx_crc+3))) {
        tx_crc = 0;
        for(i=0; i<4; i++) {
            tx_crc <<= 4;
            tx_crc |= hex2int(ptx_crc[i]);
            if (hstates->verbose){
                fprintf(stderr, "ptx_crc[%d] %c 0x%02X tx_crc: 0x%04X\n", i, ptx_crc[i], hex2int(ptx_crc[i]), tx_crc);
            }
        }
        crc_ok = (tx_crc == rx_crc);
        *(ptx_crc+4) = 0;  /* terminate ASCII string */

        if (crc_ok) {
            hstates->total_payload_bits = strlen(ascii_out)*ascii_bits;
        }
    }
    else {
        *ascii_out = 0;
    }

    if (hstates->verbose) {
        fprintf(stderr, "\n  endpacket: %d nout: %d tx_crc: 0x%04x rx_crc: 0x%04x\n",
                endpacket, nout, tx_crc, rx_crc);
    }
            
    /* make sure we don't overrun storage */
    
    if(nout > horus_get_max_ascii_out_len(hstates)){
        return 0;
    }

    hstates->crc_ok = crc_ok;
    
    return crc_ok;
}


int extract_horus_binary_v1(struct horus *hstates, char hex_out[], int uw_loc) {
    const int nfield = 8;                      /* 8 bit binary                   */
    int st = uw_loc;                           /* first bit of first char        */
    int en = uw_loc + HORUS_BINARY_V1_NUM_CODED_BITS; /* last bit of max length packet  */

    if (en > hstates->rx_bits_len){
        if (hstates->verbose) {
            fprintf(stderr,"not enough data yet");
        }
        return 0;
    }


    int      j, b, nout;
    uint8_t  rxpacket[HORUS_BINARY_V1_NUM_CODED_BITS];
    uint8_t  rxbyte, *pout;
 
    /* convert bits to a packet of bytes */
    
    pout = rxpacket; nout = 0;
    
    for (b=st; b<en; b+=nfield) {

        /* assemble bytes MSB to LSB */

        rxbyte = 0;
        for(j=0; j<nfield; j++) {
            assert(hstates->rx_bits[b+j] <= 1);
            rxbyte <<= 1;
            rxbyte |= hstates->rx_bits[b+j];
        }
        
        /* build up output array */
        
        *pout++ = rxbyte;
        nout++;
    }

    if (hstates->verbose) {
        fprintf(stderr, "  extract_horus_binary nout: %d\n  Received Packet before decoding:\n  ", nout);
        for (b=0; b<nout; b++) {
            fprintf(stderr, "%02X", rxpacket[b]);
        }
        fprintf(stderr, "\n");
    }
    
    uint8_t payload_bytes[HORUS_BINARY_V1_NUM_UNCODED_PAYLOAD_BYTES];
    horus_l2_decode_rx_packet(payload_bytes, rxpacket, HORUS_BINARY_V1_NUM_UNCODED_PAYLOAD_BYTES);

    uint16_t crc_tx, crc_rx;
    crc_rx = horus_l2_gen_crc16(payload_bytes, HORUS_BINARY_V1_NUM_UNCODED_PAYLOAD_BYTES-2);
    crc_tx = (uint16_t)payload_bytes[HORUS_BINARY_V1_NUM_UNCODED_PAYLOAD_BYTES-2] +
        ((uint16_t)payload_bytes[HORUS_BINARY_V1_NUM_UNCODED_PAYLOAD_BYTES-1]<<8);
    
    if (hstates->verbose) {
        fprintf(stderr, "  extract_horus_binary crc_tx: %04X crc_rx: %04X\n", crc_tx, crc_rx);
    }
    
    /* convert to ASCII string of hex characters */

    hex_out[0] = 0;
    char hex[3];
    for (b=0; b<HORUS_BINARY_V1_NUM_UNCODED_PAYLOAD_BYTES; b++) {
        sprintf(hex, "%02X", payload_bytes[b]);
        strcat(hex_out, hex);
    }
   
    if (hstates->verbose) {
        fprintf(stderr, "  nout: %d Decoded Payload bytes:\n  %s \n", nout, hex_out);
    }

    /* With noise input to FSK demod we can get occasinal UW matches,
       so a good idea to only pass on any packets that pass CRC */
    
    hstates->crc_ok = (crc_tx == crc_rx);
    if ( hstates->crc_ok) {
        hstates->total_payload_bits = HORUS_BINARY_V1_NUM_UNCODED_PAYLOAD_BYTES;
    }
    hstates->version = 1;
    return hstates->crc_ok;
}

int extract_horus_binary_v2_256(struct horus *hstates, char hex_out[], int uw_loc, int size) {
    const int nfield = 8;                      /* 8 bit binary                   */
    int st = uw_loc;                           /* first bit of first char        */
    int en = uw_loc + (horus_l2_get_num_tx_data_bytes(size)*8); /* last bit of max length packet  */

    int      j, b, nout;
    uint8_t  rxpacket[(horus_l2_get_num_tx_data_bytes(size)*8)];
    uint8_t  rxbyte, *pout;
 

    if (en > hstates->rx_bits_len){
        if (hstates->verbose) {
            fprintf(stderr,"not enough data yet %d %d\n", en, hstates->rx_bits_len);
        }
        return 0;
    }

    /* convert bits to a packet of bytes */
    
    pout = rxpacket; nout = 0;
    
    for (b=st; b<en; b+=nfield) {

        /* assemble bytes MSB to LSB */

        rxbyte = 0;
        for(j=0; j<nfield; j++) {
            assert(hstates->rx_bits[b+j] <= 1);
            rxbyte <<= 1;
            rxbyte |= hstates->rx_bits[b+j];
        }
        
        /* build up output array */
        
        *pout++ = rxbyte;
        nout++;
    }

    if (hstates->verbose) {
        fprintf(stderr, "  extract_horus_binary_v2_256 nout: %d\n  Received Packet before decoding:\n  ", nout);
        for (b=0; b<nout; b++) {
            fprintf(stderr, "%02X", rxpacket[b]);
        }
        fprintf(stderr, "\n");
    }
    
    uint8_t payload_bytes[size];
    horus_l2_decode_rx_packet(payload_bytes, rxpacket, size);

    uint16_t crc_tx, crc_rx;

    crc_rx = horus_l2_gen_crc16(payload_bytes, size-2);
    crc_tx = (uint16_t)payload_bytes[size-2] +
        ((uint16_t)payload_bytes[size-1]<<8);
    
    hstates->crc_ok = (crc_tx == crc_rx);
    if (!hstates->crc_ok){ // check if horus binary v3 - which has crc16 at the start of the packet
        crc_rx = horus_l2_gen_crc16(payload_bytes+2, size-2);
        crc_tx = (uint16_t)payload_bytes[0] +
            ((uint16_t)payload_bytes[1]<<8);
        if ((hstates->crc_ok = (crc_tx == crc_rx))){
            hstates->version = 3;
            if (hstates->verbose) {
                fprintf(stderr, "v3 packet\n");
            }
        }
        
    } else {
        hstates->version = 2;
    }
    
    if (hstates->verbose) {
        fprintf(stderr, "  extract_horus_binary_v2_256 crc_tx: %04X crc_rx: %04X\n", crc_tx, crc_rx);
    }
    
    /* convert to ASCII string of hex characters */

    hex_out[0] = 0;
    char hex[3];
    for (b=0; b<size; b++) {
        sprintf(hex, "%02X", payload_bytes[b]);
        strcat(hex_out, hex);
    }
   
    if (hstates->verbose) {
        fprintf(stderr, "  nout: %d Decoded Payload bytes:\n  %s\n", nout, hex_out);
    }

    /* With noise input to FSK demod we can get occasinal UW matches,
       so a good idea to only pass on any packets that pass CRC */
    
    
    if ( hstates->crc_ok) {
        hstates->total_payload_bits = size;
    }
    return hstates->crc_ok;
}

int horus_rx(struct horus *hstates, char ascii_out[], short demod_in[], int quadrature) {
    int i, j, packet_detected;
    
    assert(hstates != NULL);
    packet_detected = 0;

    int Nbits = hstates->fsk->Nbits;
    int rx_bits_len = hstates->rx_bits_len;
    
    if (hstates->verbose) {
        fprintf(stderr, "  horus_rx max_packet_len: %d rx_bits_len: %d Nbits: %d nin: %d\n",
                hstates->max_packet_len, rx_bits_len, Nbits, hstates->fsk->nin);
    }
    
    /* shift buffer of bits to make room for new bits */

    for(i=0,j=Nbits; j<rx_bits_len; i++,j++) {
        hstates->rx_bits[i] = hstates->rx_bits[j];
        hstates->soft_bits[i] = hstates->soft_bits[j];
    }





            
    /* demodulate latest bits */

    /* Note: allocating this array as an automatic variable caused OSX to
    "Bus Error 10" (segfault), so lets malloc() it. */
    
    COMP *demod_in_comp = (COMP*)malloc(sizeof(COMP)*hstates->fsk->nin);
    
    for (i=0; i<hstates->fsk->nin; i++) {
        if (quadrature) {
            demod_in_comp[i].real = demod_in[i * 2];
            demod_in_comp[i].imag = demod_in[i * 2 + 1];
        } else {
            demod_in_comp[i].real = demod_in[i];
            demod_in_comp[i].imag = 0;
        }
    }




    fsk_demod_core(hstates->fsk, &hstates->rx_bits[rx_bits_len-Nbits], &hstates->soft_bits[rx_bits_len-Nbits], demod_in_comp);
    free(demod_in_comp);
    if (hstates->uw_count ) {
        int old_uw_count = hstates->uw_count;
        hstates->uw_count = 0;
        for (int uw_idx=0; uw_idx < old_uw_count; uw_idx++){
            if (hstates->uw_loc[uw_idx]-Nbits >= 0 && hstates->uw_count < MAX_UW_TO_TRACK) 
            {
                 if (hstates->verbose) {
                    fprintf(stderr, "%d %d -> %d\n", uw_idx, hstates->uw_loc[uw_idx], hstates->uw_loc[uw_idx] - Nbits );
                }
                hstates->uw_loc[hstates->uw_count] = hstates->uw_loc[uw_idx] - Nbits;
                hstates->uw_count++;
            }
        }
        if (hstates->verbose) {
            fprintf(stderr, "updated uw states\n");
        }
    }    

    horus_find_uw(hstates);

        /* UW search to see if we can find the start of a packet in the buffer */
    for (int uw_idx=0; uw_idx < hstates->uw_count; uw_idx++){       
        if (hstates->verbose) {
            fprintf(stderr, "[%d]  horus_rx uw_loc: %d mode: %d\n", uw_idx, hstates->uw_loc[uw_idx], hstates->mode);
        }
        
        /* OK we have found a unique word, and therefore the start of
        a packet, so lets try to extract valid packets */
        if (hstates->mode == HORUS_MODE_RTTY_7N1) {
            packet_detected = extract_horus_rtty(hstates, ascii_out, hstates->uw_loc[uw_idx], 7, 1 );

            if (packet_detected){
                // If we have found a packet clear any possible UW detections nearby
                for (int uw_idx_clear=0; uw_idx_clear < hstates->uw_count; uw_idx_clear++){ 
                    if (hstates->uw_loc[uw_idx_clear]  - hstates->uw_loc[uw_idx] < 100) {
                        hstates->uw_loc[uw_idx_clear] = -1;
                    }
                }
                if (hstates->verbose) {
                    fprintf(stderr, "RTTY Detected \n");
                }
                break;
            }
        }

        if (hstates->mode == HORUS_MODE_RTTY_7N2) {
            packet_detected = extract_horus_rtty(hstates, ascii_out, hstates->uw_loc[uw_idx], 7, 2);

            if (packet_detected){
                // If we have found a packet clear any possible UW detections nearby
                for (int uw_idx_clear=0; uw_idx_clear < hstates->uw_count; uw_idx_clear++){ 
                    if (hstates->uw_loc[uw_idx_clear]  - hstates->uw_loc[uw_idx] < 100) {
                        hstates->uw_loc[uw_idx_clear] = -1;
                    }
                }
                if (hstates->verbose) {
                    fprintf(stderr, "RTTY Detected \n");
                }
                 break;
            }
        }
        if (hstates->mode == HORUS_MODE_RTTY_8N2) {
            packet_detected = extract_horus_rtty(hstates, ascii_out,hstates->uw_loc[uw_idx], 8, 2);

            if (packet_detected){
                // If we have found a packet clear any possible UW detections nearby
                for (int uw_idx_clear=0; uw_idx_clear < hstates->uw_count; uw_idx_clear++){ 
                    if (hstates->uw_loc[uw_idx_clear]  - hstates->uw_loc[uw_idx] < 100) {
                        hstates->uw_loc[uw_idx_clear] = -1;
                    }
                }
                if (hstates->verbose) {
                    fprintf(stderr, "RTTY Detected \n");
                }
                 break;
            }
        }
        if (hstates->mode == HORUS_MODE_BINARY_V1) {
            // TODO - we can optimise only checking packet sizes that are would come valid. eg, a 16byte packet isn't going to magically become valid after 64 bytes
            packet_detected = extract_horus_binary_v1(hstates, ascii_out, hstates->uw_loc[uw_idx]);
            if (!packet_detected){
                // Try v2 256 bit decoder instead
                if (hstates->verbose) {
                    fprintf(stderr, "Trying all horus sizes \n");
                }
                for (int size_idx=0; size_idx<(int)(sizeof(horus_v3_check_sizes)/sizeof(horus_v3_check_sizes[0])); size_idx++){
                    if (hstates->verbose) {
                        fprintf(stderr, "Size: %d \n", horus_v3_check_sizes[size_idx]);
                    }
                    packet_detected = extract_horus_binary_v2_256(hstates, ascii_out, hstates->uw_loc[uw_idx], horus_v3_check_sizes[size_idx]);
                    if (packet_detected){
                        break;
                    }
                }
            }
            //#define DUMP_BINARY_PACKET
            #ifdef DUMP_BINARY_PACKET
            FILE *f = fopen("packetbits.txt", "wt"); assert(f != NULL);
            for(i=0; i<hstates->max_packet_len; i++) {
                fprintf(f,"%d ", hstates->rx_bits[hstates->uw_loc+i]);
            }
            fclose(f);
            exit(0);
            #endif
        }

        if (packet_detected){
            if (hstates->verbose) {
                fprintf(stderr, "Removed uw index %d@%d - late\n", uw_idx, hstates->uw_loc[uw_idx]);
            }
            hstates->uw_loc[uw_idx] = -1; // remove this UW from further searches.

            return packet_detected;
        }

    
    }
    return packet_detected;
}

int horus_get_version(void) {
    return HORUS_API_VERSION;
}

int horus_get_mode(struct horus *hstates) {
    assert(hstates != NULL);
    return hstates->mode;
}

int horus_get_Fs(struct horus *hstates) {
    assert(hstates != NULL);
    return hstates->Fs;
}

int horus_get_mFSK(struct horus *hstates) {
    assert(hstates != NULL);
    return hstates->mFSK;
}

int horus_get_max_demod_in(struct horus *hstates) {
    /* copied from fsk_demod.c, a nicer fsk_max_nin function would be useful */
    return sizeof(short)*(hstates->fsk->N + hstates->fsk->Ts*2);
}

int horus_get_max_ascii_out_len(struct horus *hstates) {
    assert(hstates != NULL);
    if (hstates->mode == HORUS_MODE_RTTY_7N1) {
        return hstates->max_packet_len/9;     /* 7 bit ASCII, plus 3 sync bits */
    }
    if (hstates->mode == HORUS_MODE_RTTY_7N2) {
        return hstates->max_packet_len/10;     /* 7 bit ASCII, plus 3 sync bits */
    }
    if (hstates->mode == HORUS_MODE_RTTY_8N2) {
        return hstates->max_packet_len/11;     /* 8 bit ASCII, plus 3 sync bits */
    }
    if (hstates->mode == HORUS_MODE_BINARY_V1) {
        //return (HORUS_BINARY_V1_NUM_UNCODED_PAYLOAD_BYTES*2+1);     /* Hexadecimal encoded */
        return (HORUS_BINARY_V1V2_MAX_UNCODED_BYTES*2+1);
    }
    if (hstates->mode == HORUS_MODE_BINARY_V2_256BIT) {
        return (HORUS_BINARY_V1V2_MAX_UNCODED_BYTES*2+1);     /* Hexadecimal encoded */
    }
    if (hstates->mode == HORUS_MODE_BINARY_V2_128BIT) {
        return (HORUS_BINARY_V2_128BIT_NUM_UNCODED_PAYLOAD_BYTES*2+1);     /* Hexadecimal encoded */
    }
    assert(0); /* should never get here */
    return 0;
}

void horus_get_modem_stats(struct horus *hstates, int *sync, float *snr_est) {
    struct MODEM_STATS stats;
    assert(hstates != NULL);

    /* TODO set sync if UW found "recently", but WTF is recently? Maybe need a little state 
       machine to "blink" sync when we get a packet */

    *sync = 0;
    
    /* SNR scaled from Eb/No est returned by FSK to SNR in 3000 Hz */

    fsk_get_demod_stats(hstates->fsk, &stats);
    *snr_est = stats.snr_est + 10*log10((float)hstates->Rs*log2(hstates->mFSK)/3000);
}

void horus_get_modem_extended_stats (struct horus *hstates, struct MODEM_STATS *stats) {
    int i;
    
    assert(hstates != NULL);

    fsk_get_demod_stats(hstates->fsk, stats);
    if (hstates->verbose) {
        fprintf(stderr, "  horus_get_modem_extended_stats stats->snr_est: %f\n", stats->snr_est);
    }
    stats->snr_est = stats->snr_est + 10*log10((float)hstates->Rs*log2(hstates->mFSK)/3000);

    assert(hstates->mFSK <= MODEM_STATS_MAX_F_EST);
    for (i=0; i<hstates->mFSK; i++) {
        // Grab the appropriate frequency estimator data.
        if (hstates->fsk->freq_est_type){
            stats->f_est[i] = hstates->fsk->f2_est[i];
        } else {
            stats->f_est[i] = hstates->fsk->f_est[i];
        }
    }
}

void horus_set_verbose(struct horus *hstates, int verbose) {
    assert(hstates != NULL);
    hstates->verbose = verbose;
}

int horus_crc_ok(struct horus *hstates) {
    assert(hstates != NULL);
    return hstates->crc_ok;
}

int horus_packet_version(struct horus *hstates) {
    assert(hstates != NULL);
    return hstates->version;
}

int horus_get_total_payload_bits(struct horus *hstates) {
    assert(hstates != NULL);
    return hstates->total_payload_bits;
}

void horus_set_total_payload_bits(struct horus *hstates, int val) {
    assert(hstates != NULL);
    hstates->total_payload_bits = val;
}

void horus_set_freq_est_limits(struct horus *hstates, float fsk_lower, float fsk_upper) {
    assert(hstates != NULL);
    assert(fsk_upper > fsk_lower);
    hstates->fsk->est_min = fsk_lower;
    hstates->fsk->est_max = fsk_upper;    
}
