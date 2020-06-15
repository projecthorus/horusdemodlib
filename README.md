# High Altitude Balloon (HAB) telemetry library

## Building

```
$ git clone https://github.com/drowe67/codec2.git
$ cd codec2 && mkdir build_linux && cd build_linux && cmake ../ && make
$ cd ~
$ git clone https://github.com/drowe67/hab.git
$ cd hab && mkdir build_linux && cd build_linux
$ cmake -DCODEC2_BUILD_DIR=~/codec2/build_linux ..
$ make
```

## Testing

```
$ cd hab/build_linux
$ ctest
```

## Further Reading

   Here are some links to projects and blog posts that use this code:

   1. [Horus Binary](https://github.com/projecthorus/horusbinary) High Altitude Balloon (HAB) telemetry protocol, 3 second updates, works at 7dB lower SNR that RTTY.
   1. [Testing HAB Telemetry, Horus binary waveform](http://www.rowetel.com/?p=5906)
   1. [Wenet](https://github.com/projecthorus/wenet) - high speed SSTV images from balloons at the edge of space
   1. [Wenet High speed SSTV images](http://www.rowetel.com/?p=5344)
