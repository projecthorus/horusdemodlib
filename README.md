# High Altitude Balloon (HAB) Telemetry Library

This library contains software used to encode and decode telemetry used by the Project Horus High-Altitude Balloon (HAB) project (amongst other users). This software was originally developed as part of the [codec2](https://github.com/drowe67/codec2) project, but as of 2020 has been broken out into this separate project, to keep codec2 targeted at low-level voice-codec and modem development.

This library includes the following:
* The 'HorusBinary' demodulator, a high performance 4FSK modem used for low-rate positional telemetry from HABs. More information on this modem can be found here: https://github.com/projecthorus/horusbinary  (This repository will eventually be re-worked to use this library)
* The 'Wenet' demodulator, used to downlink imagery from HAB payloads. 


## HorusDemodLib C Library
This contains the demodulator portions of horuslib, which are written in C.

## Building

```
$ git clone https://github.com/projecthorus/horusdemodlib.git
$ cd horusdemodlib && mkdir build && cd build
$ cmake ..
$ make
$ make install
```

## Testing

```
$ cd build
$ ctest
```

## HorusDemodLib Python Wrapper

```
$ pip install -r requirements.txt
$ pip install -e .
```


## Further Reading

   Here are some links to projects and blog posts that use this code:

   1. [Horus Binary](https://github.com/projecthorus/horusbinary) High Altitude Balloon (HAB) telemetry protocol, 3 second updates, works at 7dB lower SNR that RTTY.
   1. [Testing HAB Telemetry, Horus binary waveform](http://www.rowetel.com/?p=5906)
   1. [Wenet](https://github.com/projecthorus/wenet) - high speed SSTV images from balloons at the edge of space
   1. [Wenet High speed SSTV images](http://www.rowetel.com/?p=5344)
