#!/usr/bin/env bash
#
#	Dual Horus Binary Decoder Script
#	Intended for use with Dual Launches, where both launches have 4FSK payloads closely spaced (~10 kHz)
#
#	The SDR is tuned 5 kHz below the Lower 4FSK frequency, and the frequency estimators are set across the two frequencies.
# 	Modem statistics are sent out via a new 'MODEM_STATS' UDP broadcast message every second.
#

# Calculate the frequency estimator limits
# Note - these are somewhat hard-coded for this dual-RX application.
MFSK1_LOWER=$(echo "$MFSK1_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK1_UPPER=$(echo "$MFSK1_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK1_CENTRE=$(echo "$RXFREQ + $MFSK1_SIGNAL" | bc)

MFSK2_LOWER=$(echo "$MFSK2_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK2_UPPER=$(echo "$MFSK2_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK2_CENTRE=$(echo "$RXFREQ + $MFSK2_SIGNAL" | bc)

echo "Using SDR Centre Frequency: $RXFREQ Hz."
echo "Using MFSK1 estimation range: $MFSK1_LOWER - $MFSK1_UPPER Hz"
echo "Using MFSK2 estimation range: $MFSK2_LOWER - $MFSK2_UPPER Hz"

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

STATS_SETTING=""

if [ "$STATS_OUTPUT" = "1" ]; then
	echo "Enabling Modem Statistics."
	STATS_SETTING=" --stats=100"
fi

# Start the receive chain.
# Note that we now pass in the SDR centre frequency ($RXFREQ) and 'target' signal frequency ($MFSK1_CENTRE)
# to enable providing additional metadata to Habitat / Sondehub.
rtl_fm -M raw -F9 -s 48000 -p $PPM $GAIN_SETTING$BIAS_SETTING -f $RXFREQ | tee >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK1_LOWER --fsk_upper=$MFSK1_UPPER - - | python3 -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK1_CENTRE ) >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK2_LOWER --fsk_upper=$MFSK2_UPPER - - | python3 -m horusdemodlib.uploader --freq_hz $RXFREQ ) > /dev/null
