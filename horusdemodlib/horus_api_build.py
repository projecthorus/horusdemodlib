from cffi import FFI
import re
import platform

ffibuilder = FFI()


def preprocess_h():
    # data = open("./horusdemodlib/src/horus_api.h", "r").read()
    # data += open("./horusdemodlib/src/modem_stats.h", "r").read()
    # data = re.sub(r'#ifdef.+?#endif','',data, flags=re.DOTALL)
    # data = re.sub(r'#ifndef.+\n','',data)
    # data = re.sub(r'#include.+\n','',data)
    # data = re.sub(r'#endif.*\n','',data)

    # # searches for defines using defines and replaces them
    # max_loop = 100
    # while defines := re.findall(r'^#define +(\w+) +(?!\d+(?: +.*$)?$)(\w+)(?: +.*)?$',data, flags=re.MULTILINE):
    #     current_define_values = re.findall(r'^#define +(\w+) +(\d+)(?: +.*)?$',data, flags=re.MULTILINE)
    #     current_define_values = { x[0]: x[1] for x in current_define_values}
    #     for define in defines:
    #         print(define)
    #         if define[1] in current_define_values:
    #             data = re.sub('^(#define +'+define[0]+' +)(\w+)((?: +.*)?)$','\\1 '+current_define_values[define[1]]+' \\3', data, flags=re.MULTILINE)
    #     if max_loop == 0:
    #         raise ValueError("Could not replace out all #defines with primatives")
        
    # current_define_values = re.findall(r'^#define +(\w+) +(\d+)(?: +.*)?$',data, flags=re.MULTILINE)
    # current_define_values = { x[0]: int(x[1]) for x in current_define_values}
    # # searches for maths
    # for math_define in re.findall(r'^#define +(\w+) +\((.+?)\)(?: +.*)?$',data, flags=re.MULTILINE):
    #     value = eval(math_define[1],current_define_values)
    #     data = re.sub('^(#define +'+math_define[0]+' +)(.+)((?: +.*)?)$','\\1 '+str(value)+' \\3', data, flags=re.MULTILINE)
    # print(data)
    data = """
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


#define HORUS_BINARY_V1V2_MAX_BITS       520  
#define HORUS_BINARY_V1V2_MAX_UNCODED_BYTES    32 

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
#define HORUS_RTTY_7N1_NUM_BITS                  1080 
#define HORUS_RTTY_7N2_NUM_BITS                  1200 
#define HORUS_RTTY_8N2_NUM_BITS                  1320 
#define HORUS_RTTY_DEFAULT_BAUD                 100

struct horus;
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
  * int P - Oversampling rate. (Fs/Rs)%P should equal 0 other the modem will be sad.

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



/*---------------------------------------------------------------------------*\

  FILE........: modem_stats.h
  AUTHOR......: David Rowe
  DATE CREATED: June 2015

  Common structure for returning demod stats from fdmdv and cohpsk modems.

\*---------------------------------------------------------------------------*/

/*
  Copyright (C) 2015 David Rowe

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





#define MODEM_STATS_NC_MAX      50
#define MODEM_STATS_NR_MAX      8
#define MODEM_STATS_ET_MAX      8
#define MODEM_STATS_EYE_IND_MAX 160     
#define MODEM_STATS_NSPEC       512
#define MODEM_STATS_MAX_F_HZ    4000
#define MODEM_STATS_MAX_F_EST   4
      

typedef struct {
  float real;
  float imag;
} COMP;


typedef struct {
    float r;
    float i;
}kiss_fft_cpx;

typedef struct kiss_fft_state* kiss_fft_cfg;

    
struct MODEM_STATS {
    int    Nc;
    float  snr_est;                          /* estimated SNR of rx signal in dB (3 kHz noise BW)  */
    COMP   rx_symbols[MODEM_STATS_NR_MAX][MODEM_STATS_NC_MAX+1];
                                             /* latest received symbols, for scatter plot          */
    int    nr;                               /* number of rows in rx_symbols                       */
    int    sync;                             /* demod sync state                                   */
    float  foff;                             /* estimated freq offset in Hz                        */
    float  rx_timing;                        /* estimated optimum timing offset in samples         */
    float  clock_offset;                     /* Estimated tx/rx sample clock offset in ppm         */
    float  sync_metric;                      /* number between 0 and 1 indicating quality of sync  */
    
    /* eye diagram traces */
    /* Eye diagram plot -- first dim is trace number, second is the trace idx */
    float  rx_eye[MODEM_STATS_ET_MAX][MODEM_STATS_EYE_IND_MAX];
    int    neyetr;                           /* How many eye traces are plotted */
    int    neyesamp;                         /* How many samples in the eye diagram */

    /* optional for FSK modems - est tone freqs */

    float f_est[MODEM_STATS_MAX_F_EST];
    
    /* Buf for FFT/waterfall */

   float        fft_buf[2*MODEM_STATS_NSPEC];
   kiss_fft_cfg fft_cfg;
   
};

int horus_l2_get_num_tx_data_bytes(int num_payload_data_bytes);

/* call this first */

void horus_l2_init(void);

/* returns number of output bytes in output_tx_data */

int horus_l2_encode_tx_packet(unsigned char *output_tx_data,
                              unsigned char *input_payload_data,
                              int            num_payload_data_bytes);

void horus_l2_decode_rx_packet(unsigned char *output_payload_data,
                               unsigned char *input_rx_data,
                               int            num_payload_data_bytes);

unsigned short horus_l2_gen_crc16(unsigned char* data_p, unsigned char length);

"""
    return data

ffibuilder.cdef(preprocess_h()
    
)

# set_source() gives the name of the python extension module to
# produce, and some C source code as a string.  This C code needs
# to make the declarated functions, types and globals available,
# so it is often just the "#include".

ffibuilder.set_source("_horus_api_cffi",
"""
     #include "horus_api.h"   // the C header of the library
     #include "horus_l2.h"
""",
      sources=[
        "./src/fsk.c",
        "./src/kiss_fft.c",
        "./src/kiss_fftr.c",
        "./src/mpdecode_core.c",
        "./src/H_256_768_22.c",
        "./src/H_128_384_23.c",
        "./src/golay23.c",
        "./src/phi0.c",
        "./src/horus_api.c",
        "./src/horus_l2.c",
      ],
       include_dirs = [ "./src"],
       extra_compile_args = ["-DHORUS_L2_RX","-DINTERLEAVER","-DSCRAMBLER","-DRUN_TIME_TABLES"],
       # ideally we would detect mingw32 compiler but that appears to be hard
       extra_link_args = ["-static"] if platform.system() == "Windows" else []
     )   # library name, for the linker

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)