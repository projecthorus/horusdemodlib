#!/usr/bin/env bash
#
#	Dual RTTY / Horus Binary Decoder Script
#	Intended for use on Horus flights, with the following payload frequencies:
#	RTTY: 434.650 MHz - Callsign 'HORUS'
#	MFSK: 434.660 MHz - Callsign 'HORUSBINARY'
#
#	The SDR is tuned 5 kHz below the RTTY frequency, and the frequency estimators are set across the two frequencies.
# 	Modem statistics are sent out via a new 'MODEM_STATS' UDP broadcast message every second.
#

# Calculate the frequency estimator limits
# Note - these are somewhat hard-coded for this dual-RX application.
RTTY_LOWER=$(echo "$RTTY_SIGNAL - $RXBANDWIDTH/2" | bc)
RTTY_UPPER=$(echo "$RTTY_SIGNAL + $RXBANDWIDTH/2" | bc)
RTTY_CENTRE=$(echo "$RXFREQ + $RTTY_SIGNAL" | bc)

MFSK_LOWER=$(echo "$MFSK_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK_UPPER=$(echo "$MFSK_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK_CENTRE=$(echo "$RXFREQ + $MFSK_SIGNAL" | bc)

echo "Using SDR Centre Frequency: $RXFREQ Hz."
echo "Using RTTY estimation range: $RTTY_LOWER - $RTTY_UPPER Hz"
echo "Using MFSK estimation range: $MFSK_LOWER - $MFSK_UPPER Hz"

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
# Note that we now pass in the SDR centre frequency ($RXFREQ) and 'target' signal frequency ($RTTY_CENTRE / $MFSK_CENTRE)
# to enable providing additional metadata to Habitat / Sondehub.
rtl_fm -M raw -F9 -s 48000 -p $PPM $GAIN_SETTING$BIAS_SETTING -f $RXFREQ | tee >($DECODER -q --stats=5 -g -m RTTY --fsk_lower=$RTTY_LOWER --fsk_upper=$RTTY_UPPER - - | python3 -m horusdemodlib.uploader --rtty --freq_hz $RXFREQ --freq_target_hz $RTTY_CENTRE ) >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK_LOWER --fsk_upper=$MFSK_UPPER - - | python3 -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK_CENTRE ) > /dev/null
