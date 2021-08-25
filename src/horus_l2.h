/*---------------------------------------------------------------------------*\

  FILE........: horus_l2.h
  AUTHOR......: David Rowe
  DATE CREATED: Dec 2015

\*---------------------------------------------------------------------------*/

#ifndef __HORUS_L2__
#define __HORUS_L2__

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

// int ldpc_encode_packet(uint8_t *buff_mfsk, uint8_t *FSK, int mode);

// void soft_unscramble(float *in, float* out, int nbits);
// void soft_deinterleave(float *in, float* out, int mode);
// void horus_ldpc_decode(uint8_t *payload, float *sd, int mode);

#endif
