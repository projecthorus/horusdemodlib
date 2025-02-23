#!/usr/bin/env bash
#
#	Horus Binary KA9Q-Radio Helper Script
#
#   Uses ka9q-radio (pcmrecord) to receive a chunk of spectrum, and passes it into horus_demod.
#

# Calculate the frequency estimator limits
FSK_LOWER=$(echo "$RXBANDWIDTH / -2" | bc)
FSK_UPPER=$(echo "$RXBANDWIDTH / 2" | bc)

SSRC=$(($RXFREQ / 1000))01
RADIO=$(echo $SDR_DEVICE | sed 's/-pcm//g')

echo "Using SDR Centre Frequency: $RXFREQ Hz"
echo "Using SSRC: $SSRC"
echo "Using PCM stream: $SDR_DEVICE"
echo "Using FSK estimation range: $FSK_LOWER - $FSK_UPPER Hz"

cleanup () {
    echo "Closing channel $SSRC at frequency $RXFREQ"
    tune --samprate 48000 --mode iq --low $FSK_LOWER --high $FSK_UPPER --frequency 0 --ssrc $SSRC --radio $RADIO
}

trap cleanup EXIT

# Start the receive chain.
# Note that we now pass in the SDR centre frequency ($RXFREQ) and 'target' signal frequency ($RXFREQ)
# to enable providing additional metadata to Habitat / Sondehub.
echo "Configuring receiver on ka9q-radio"
tune --samprate 48000 --mode iq --low $FSK_LOWER --high $FSK_UPPER --frequency $RXFREQ --ssrc $SSRC --radio $RADIO

echo "Starting receiver chain"
pcmrecord --ssrc $SSRC --catmode --raw $SDR_DEVICE | $DECODER -q --stats=5 -g -m binary --fsk_lower=$FSK_LOWER --fsk_upper=$FSK_UPPER - - | python3 -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $RXFREQ $@