/*---------------------------------------------------------------------------*\

  FILE........: horus_api.h
  AUTHOR......: David Rowe
  DATE CREATED: March 2018

  Library of API functions that implement High Altitude Balloon (HAB)
  telemetry modems and protocols.

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

#ifdef __cplusplus
  extern "C" {
#endif

#ifndef __HORUS_API__

#include <stdint.h>
#include "modem_stats.h"
      
/* Horus API Modes */
#define HORUS_MODE_BINARY_V1            0  // Legacy binary mode
#define HORUS_MODE_BINARY_V2_256BIT     1  // New 256-bit Golay Encoded Mode
#define HORUS_MODE_BINARY_V2_128BIT     2  // New 128-bit Golay Encoded Mode (Not used yet)
#define HORUS_MODE_RTTY_7N1             89 // RTTY Decoding - 7N1
#define HORUS_MODE_RTTY_7N2             90 // RTTY Decoding - 7N2
#define HORUS_MODE_RTTY_8N2             91 // RTTY Decoding - 8N2


// Settings for Legacy Horus Binary Mode (Golay (23,12) encoding)
#define HORUS_BINARY_V1_NUM_CODED_BITS             360
#define HORUS_BINARY_V1_NUM_UNCODED_PAYLOAD_BYTES  22
#define HORUS_BINARY_V1_DEFAULT_BAUD               100
#define HORUS_BINARY_V1_DEFAULT_TONE_SPACING       270  // This is the minimum tone spacing possible on the RS41 
                                                        // reference implementation of this modem.
                                                        // Note that mask estimation is turned off by default for 
                                                        // this mode, and hence this spacing is not used.

// Settings for Horus Binary 256-bit mode (Golay (23,12) encoding)
#define HORUS_BINARY_V2_256BIT_NUM_CODED_BITS               520
#define HORUS_BINARY_V2_256BIT_NUM_UNCODED_PAYLOAD_BYTES    32
#define HORUS_BINARY_V2_256BIT_DEFAULT_BAUD                 100
#define HORUS_BINARY_V2_256BIT_DEFAULT_TONE_SPACING         270

// Settings for Horus Binary 128-bit mode (Golay (23,12) encoding) - not used yet
#define HORUS_BINARY_V2_128BIT_NUM_CODED_BITS                  272
#define HORUS_BINARY_V2_128BIT_NUM_UNCODED_PAYLOAD_BYTES       16
#define HORUS_BINARY_V2_128BIT_DEFAULT_BAUD                    100
#define HORUS_BINARY_V2_128BIT_DEFAULT_TONE_SPACING            270 


#define HORUS_BINARY_V1V2_MAX_BITS      HORUS_BINARY_V2_256BIT_NUM_CODED_BITS * 7
#define HORUS_BINARY_V1V2_MAX_UNCODED_BYTES   128

// Not using LDPC any more...
// // Settings for Horus Binary 256-bit mode (LDPC Encoding, r=1/3)
// #define HORUS_BINARY_V2_256BIT_NUM_CODED_BITS               (768+32)
// #define HORUS_BINARY_V2_256BIT_NUM_UNCODED_PAYLOAD_BYTES    32
// #define HORUS_BINARY_V2_256BIT_DEFAULT_BAUD                 100
// #define HORUS_BINARY_V2_256BIT_DEFAULT_TONE_SPACING         270

// // Settings for Horus Binary 128-bit mode (LDPC Encoding, r=1/3)
// #define HORUS_BINARY_V2_128BIT_NUM_CODED_BITS                  (384+32)
// #define HORUS_BINARY_V2_128BIT_NUM_UNCODED_PAYLOAD_BYTES       16
// #define HORUS_BINARY_V2_128BIT_DEFAULT_BAUD                    100
// #define HORUS_BINARY_V2_128BIT_DEFAULT_TONE_SPACING            270 


// Settings for RTTY Decoder
#define HORUS_RTTY_MAX_CHARS                    120
#define HORUS_RTTY_7N1_NUM_BITS                 (HORUS_RTTY_MAX_CHARS*9)
#define HORUS_RTTY_7N2_NUM_BITS                 (HORUS_RTTY_MAX_CHARS*10)
#define HORUS_RTTY_8N2_NUM_BITS                 (HORUS_RTTY_MAX_CHARS*11)
#define HORUS_RTTY_DEFAULT_BAUD                 100



#define MAX_UW_LENGTH                  100
#define HORUS_API_VERSION                3    /* unique number that is bumped if API changes */

#define MAX_UW_TO_TRACK 32

struct horus {
    int         mode;
    int         verbose;
    struct FSK *fsk;                                  /* states for FSK modem                */
    int         Fs;                                   /* sample rate in Hz                   */
    int         mFSK;                                 /* number of FSK tones                 */
    int         Rs;                                   /* symbol rate in Hz                   */
    int         uw[MAX_UW_LENGTH];                    /* unique word bits mapped to +/-1     */
    int         uw_thresh;                            /* threshold for UW detection          */
    int         uw_len;                               /* length of unique word               */
    int         max_packet_len;                       /* max length of a telemetry packet    */
    uint8_t    *rx_bits;                              /* buffer of received bits             */
    float      *soft_bits;                            /* buffer of soft decision outputs     */
    int         rx_bits_len;                          /* length of rx_bits buffer            */
    int         crc_ok;                               /* most recent packet checksum results */
    int         total_payload_bits;                   /* num bits rx-ed in last RTTY packet  */
    int         uw_loc[MAX_UW_TO_TRACK];              /* current location of uw */
    int         uw_count;
    int         version;                              /* The version of the last decoded frame (if horus) */
};
struct MODEM_STATS;

/*
 * Create an Horus Demod config/state struct using default mode parameters.
 * 
 * int mode - Horus Mode Type (refer list above)
 */
struct horus *horus_open  (int mode);

/*
 * Create an Horus Demod config/state struct with more customizations.
 * 
 * int mode - Horus Mode Type (refer list above)
 * int Rs - Symbol Rate (Hz). Set to -1 to use the default value for the mode (refer above)
 * int tx_tone_spacing - FSK Tone Spacing, to configure mask estimator. Set to -1 to disable mask estimator.
 */

struct horus *horus_open_advanced (int mode, int Rs, int tx_tone_spacing);

/*
 * Create an Horus Demod config/state struct with more customizations.
 * 
 * int mode - Horus Mode Type (refer list above)
 * int Rs - Symbol Rate (Hz). Set to -1 to use the default value for the mode (refer above)
 * int tx_tone_spacing - FSK Tone Spacing, to configure mask estimator. Set to -1 to disable mask estimator.
 * int Fs - Sample rate
 * int P - Oversamplig rate. (Fs/Rs)%P should equal 0 other the modem will be sad.
 */

 struct horus *horus_open_advanced_sample_rate (int mode, int Rs, int tx_tone_spacing, int Fs, int P);


/*
 * Close a Horus demodulator struct and free memory.
 */
void          horus_close (struct horus *hstates);

/* call before horus_rx() to determine how many shorts to pass in */

uint32_t      horus_nin   (struct horus *hstates);

/*
 * Demodulate some number of Horus modem samples. The number of samples to be 
 * demodulated can be found by calling horus_nin().
 * 
 * Returns 1 if the data in ascii_out[] is valid.
 * 
 * struct horus *hstates - Horus API config/state struct, set up by horus_open / horus_open_advanced
 * char ascii_out[] - Buffer for returned packet / text.
 * short fsk_in[] - nin samples of modulated FSK.
 * int quadrature - Set to 1 if input samples are complex samples.
 */
      
int           horus_rx    (struct horus *hstates, char ascii_out[], short demod_in[], int quadrature);

/* set verbose level */
      
void horus_set_verbose(struct horus *hstates, int verbose);
      
/* functions to get information from API  */
      
int           horus_get_version              (void);
int           horus_get_mode                 (struct horus *hstates);
int           horus_get_Fs                   (struct horus *hstates);      
int           horus_get_mFSK                 (struct horus *hstates);      
void          horus_get_modem_stats          (struct horus *hstates, int *sync, float *snr_est);
void          horus_get_modem_extended_stats (struct horus *hstates, struct MODEM_STATS *stats);
int           horus_crc_ok                   (struct horus *hstates);
int           horus_get_total_payload_bits   (struct horus *hstates);
void          horus_set_total_payload_bits   (struct horus *hstates, int val);
void          horus_set_freq_est_limits      (struct horus *hstates, float fsk_lower, float fsk_upper);

/* how much storage you need for demod_in[] and  ascii_out[] */
      
int           horus_get_max_demod_in         (struct horus *hstates);
int           horus_get_max_ascii_out_len    (struct horus *hstates);

#endif

#ifdef __cplusplus
}
#endif
