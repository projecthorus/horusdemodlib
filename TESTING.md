# Decoder / Encoder Testing Notes

## Generating Test Frames
`horus_gen_test_bits` can be used to generate either horus v1 (mode 0) or horus v2 (mode 1) frames, in one-bit-per-byte format.

```
$ ./horus_gen_test_bits 0 1000 > horus_v1_test_frames.bin
```

These can be piped into fsk_mod to produce modulated audio:
```
$ ./horus_gen_test_bits 0 100 | ./fsk_mod 4 48000 100 1000 270 - - > horus_v1_test_frames_8khz.raw
```

You can play the frames out your speakers using sox:
```
$ ./horus_gen_test_bits 0 100 | ./fsk_mod 4 48000 100 1000 270 - - | play -t raw -r 48000 -e signed-integer -b 16 -c 1 -
```

... or pipe them straight back into horus_demod and decode them:
```
$ ./horus_gen_test_bits 0 100 | ./fsk_mod 4 48000 100 1000 270 - - | ./horus_demod -m binary - -
Using Horus Mode 0.
Generating 100 frames.
0000000000000000000000000000000000000000B8F6
0001000000000000000000000000000000000000A728
0002000000000000000000000000000000000000A75A
0003000000000000000000000000000000000000B884
... continues.
```

If we get the cohpsk_ch utility from the codec2 repository, then we can also add noise:
```
./horus_gen_test_bits 0 100 | ./fsk_mod 4 8000 100 1000 270 - - | ./cohpsk_ch - - -24 | sox -t raw -r 8000 -e signed-integer -b 16 -c 1 - -r 48000 -t raw - | ./horus_demod -m binary - -
```
In this case, we are adding enough noise that the decoder is barely hanging on. Have a listen to the signal:
```
$ ./horus_gen_test_bits 0 100 | ./fsk_mod 4 8000 100 1000 270 - - | ./cohpsk_ch - - -24 | play -t raw -r 8000 -e signed-integer -b 16 -c 1 -
```

Note that we have to use a 8kHz sample rate for cohpsk_ch to work, and hence we use sox to get the audio back into the 48 kHz sample rate expected by horus_demod.