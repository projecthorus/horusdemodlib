#!/usr/bin/env bash
#
#	Horus Binary RTLSDR Helper Script
#
#   Uses rtl_fm to receive a chunk of spectrum, and passes it into horus_demod.
#

# Calculate the SDR tuning frequency
SDR_RX_FREQ=$(echo "$RXFREQ - $RXBANDWIDTH/2 - 1000" | bc)

# Calculate the frequency estimator limits
FSK_LOWER=1000
FSK_UPPER=$(echo "$FSK_LOWER + $RXBANDWIDTH" | bc)

echo "Using SDR Centre Frequency: $SDR_RX_FREQ Hz."
echo "Using FSK estimation range: $FSK_LOWER - $FSK_UPPER Hz"

BIAS_SETTING=""

if [ "$BIAS" = "1" ]; then
	echo "Enabling Bias Tee."
	BIAS_SETTING=" -T"
fi

GAIN_SETTING=""
if [ "$GAIN" = "0" ]; then
	echo "Using AGC."
	GAIN_SETTING=""
else
	echo "Using Manual Gain"
	GAIN_SETTING=" -g $GAIN"
fi

# Start the receive chain.
# Note that we now pass in the SDR centre frequency ($SDR_RX_FREQ) and 'target' signal frequency ($RXFREQ)
# to enable providing additional metadata to Habitat / Sondehub.
rx_fm $SDR_EXTRA -M raw -F9 -s 48000 -p $PPM $GAIN_SETTING$BIAS_SETTING -f $SDR_RX_FREQ | $DECODER -q --stats=5 -g -m binary --fsk_lower=$FSK_LOWER --fsk_upper=$FSK_UPPER - - | python3 -m horusdemodlib.uploader --freq_hz $SDR_RX_FREQ --freq_target_hz $RXFREQ $@

