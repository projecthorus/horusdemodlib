/* ldpc interface to decoder
 *
 * 	It is expected that the switch to ldpc will give a 60% speed improvement
 * over golay code, with no loss of performance over white noise - the use of
 * soft-bit detection and longer codewords compensating for the expected 2dB loss
 * from reducing the number of parity bits.
 *
 * Golay code can reliably correct a 10% BER, equivalent to a 20% loss of signal
 * during deep fading. It is not clear how well ldpc will cope with deep fading,
 * but the shorter packers are bound to be more badly affected.
 */


#include <stdint.h>
#ifndef _USE_MATH_DEFINES 
#define _USE_MATH_DEFINES 
#endif
#include "math.h"
#include "string.h"
#include "mpdecode_core.h"
#include "horus_l2.h"
#include "H_128_384_23.h"
#include "H_256_768_22.h"


#define MAX_ITER         20

/* Scramble and interleave are 8bit lsb, but bitstream is sent msb */
#define LSB2MSB(X) (X + 7 - 2 * (X & 7) )

/* Invert bits - ldpc expects negative floats for high hits */
void soft_unscramble(float *in, float* out, int nbits) {
	int i, ibit;
	uint16_t scrambler = 0x4a80;  /* init additive scrambler at start of every frame */
	uint16_t scrambler_out;

	for ( i = 0; i < nbits; i++ ) {
		scrambler_out = ( (scrambler >> 1) ^ scrambler) & 0x1;

		/* modify i-th bit by xor-ing with scrambler output sequence */
		ibit = LSB2MSB(i);
		if ( scrambler_out ) {
			out[ibit] = in[ibit];
		} else {
			out[ibit] = -in[ibit];
		}

		scrambler >>= 1;
		scrambler |= scrambler_out << 14;
	}
}

// soft bit deinterleave
void soft_deinterleave(float *in, float* out, int mode) {
	int n, i, j, bits_per_packet, coprime;

    if (mode == 1) {
        // 256_768
        bits_per_packet = H_256_768_22_BITS_PER_PACKET;
        coprime = H_256_768_22_COPRIME;
    } else {
        bits_per_packet = H_128_384_23_BITS_PER_PACKET;
        coprime = H_128_384_23_COPRIME;
    }


	for ( n = 0; n < bits_per_packet; n++ ) {
		i = LSB2MSB(n);
		j = LSB2MSB( (coprime * n) % bits_per_packet);
		out[i] = in[j];
	}
}

// // packed bit deinterleave - same as Golay version , but different Coprime
// void bitwise_deinterleave(uint8_t *inout, int nbytes)
// {
//     uint16_t nbits = (uint16_t)nbytes*8;
//     uint32_t i, j, ibit, ibyte, ishift, jbyte, jshift;
//     uint8_t out[nbytes];

//     memset(out, 0, nbytes);
//     for(j = 0; j < nbits; j++) {
//         i = (COPRIME * j) % nbits;

//         /* read bit i */
//         ibyte = i>>3;
//         ishift = i&7;
//         ibit = (inout[ibyte] >> ishift) & 0x1;

// 	/* write bit i to bit j position */
//         jbyte = j>>3;
//         jshift = j&7;
//         out[jbyte] |= ibit << jshift;
//     }
 
//     memcpy(inout, out, nbytes);
// }

// /* Compare detected bits to corrected bits */
// void ldpc_errors( const uint8_t *outbytes, uint8_t *rx_bytes ) {
// 	int	length = DATA_BYTES + PARITY_BYTES;
// 	uint8_t temp[length];
// 	int	i, percentage, count = 0;
// 	memcpy(temp, rx_bytes, length);

// 	scramble(temp, length); // use scrambler from Golay code
// 	bitwise_deinterleave(temp, length);

// 	// count bits changed during error correction
// 	for(i = 0; i < BITS_PER_PACKET; i++) {
// 		int x, y, offset, shift;

// 		shift = i & 7;
// 		offset = i >> 3;
// 		x = temp[offset] >> shift;
// 		y = outbytes[offset] >> shift;
// 		count += (x ^ y) & 1;
// 	}

// 	// scale errors against a maximum of 20% BER
// 	percentage = (count * 5 * 100) / BITS_PER_PACKET;
// 	if (percentage > 100)
// 		percentage = 100;
// 	set_error_count( percentage );
// }

/* LDPC decode */
void horus_ldpc_decode(uint8_t *payload, float *sd, int mode) {
	float sum, mean, sumsq, estEsN0, x;
    int bits_per_packet;

    if(mode == 1){
        bits_per_packet = H_256_768_22_BITS_PER_PACKET;
    } else {
        bits_per_packet = H_128_384_23_BITS_PER_PACKET;
    }

    float llr[bits_per_packet];
    float temp[bits_per_packet];
    uint8_t outbits[bits_per_packet];

	int b, i, parityCC;
	struct LDPC ldpc;

	/* normalise bitstream to log-like */
	sum = 0.0;
	for ( i = 0; i < bits_per_packet; i++ )
		sum += fabs(sd[i]);
	mean = sum / bits_per_packet;

	sumsq = 0.0;
	for ( i = 0; i < bits_per_packet; i++ ) {
		x = fabs(sd[i]) / mean - 1.0;
		sumsq += x * x;
	}
	estEsN0 =  2.0 * bits_per_packet / (sumsq + 1.0e-3) / mean;
	for ( i = 0; i < bits_per_packet; i++ )
		llr[i] = estEsN0 * sd[i];

	/* reverse whitening and re-order bits */
	soft_unscramble(llr, temp, bits_per_packet);
	soft_deinterleave(temp, llr, mode);

	/* correct errors */
    if (mode == 1){
        // 32-byte mode H_256_768_22
        ldpc.max_iter = H_256_768_22_MAX_ITER;
        ldpc.dec_type = 0;
        ldpc.q_scale_factor = 1;
        ldpc.r_scale_factor = 1;
        ldpc.CodeLength = H_256_768_22_CODELENGTH;
        ldpc.NumberParityBits = H_256_768_22_NUMBERPARITYBITS;
        ldpc.NumberRowsHcols = H_256_768_22_NUMBERROWSHCOLS;
        ldpc.max_row_weight = H_256_768_22_MAX_ROW_WEIGHT;
        ldpc.max_col_weight = H_256_768_22_MAX_COL_WEIGHT;
        ldpc.H_rows = (uint16_t *)H_256_768_22_H_rows;
        ldpc.H_cols = (uint16_t *)H_256_768_22_H_cols;
    } else {
        // 16-byte mode
        ldpc.max_iter = H_128_384_23_MAX_ITER;
        ldpc.dec_type = 0;
        ldpc.q_scale_factor = 1;
        ldpc.r_scale_factor = 1;
        ldpc.CodeLength = H_128_384_23_CODELENGTH;
        ldpc.NumberParityBits = H_128_384_23_NUMBERPARITYBITS;
        ldpc.NumberRowsHcols = H_128_384_23_NUMBERROWSHCOLS;
        ldpc.max_row_weight = H_128_384_23_MAX_ROW_WEIGHT;
        ldpc.max_col_weight = H_128_384_23_MAX_COL_WEIGHT;
        ldpc.H_rows = (uint16_t *)H_128_384_23_H_rows;
        ldpc.H_cols = (uint16_t *)H_128_384_23_H_cols;
    }

	i = run_ldpc_decoder(&ldpc, outbits, llr, &parityCC);

	/* convert MSB bits to a packet of bytes */    
	for (b = 0; b < (bits_per_packet/8); b++) {
		uint8_t rxbyte = 0;
		for(i=0; i<8; i++)
			rxbyte |= outbits[b*8+i] << (7 - i);
		payload[b] = rxbyte;
	}
}
