FROM debian:bookworm-slim AS builder
LABEL org.opencontainers.image.authors="sa2kng <knegge@gmail.com>"

# ka9q-radio commit:
ARG KA9Q_REF=cc22b5f5e3c26c37df441ebff29eea7d59031afd

RUN apt-get -y update && apt-get -y upgrade && apt-get -y install --no-install-recommends \
    cmake build-essential ca-certificates git libusb-1.0-0-dev \
    libatlas-base-dev libsoapysdr-dev soapysdr-module-all \
    libairspy-dev libairspyhf-dev libavahi-client-dev libbsd-dev \
    libfftw3-dev libhackrf-dev libiniparser-dev libncurses5-dev \
    libopus-dev librtlsdr-dev libusb-1.0-0-dev libusb-dev \
    portaudio19-dev libasound2-dev libogg-dev uuid-dev rsync unzip && \
    rm -rf /var/lib/apt/lists/*

# install everything in /target and it will go in to / on destination image. symlink make it easier for builds to find files installed by this.
RUN mkdir -p /target/usr && rm -rf /usr/local && ln -sf /target/usr /usr/local && mkdir /target/etc

COPY . /horusdemodlib

RUN cd /horusdemodlib &&\
    cmake -B build -DCMAKE_INSTALL_PREFIX=/target/usr -DCMAKE_BUILD_TYPE=Release &&\
    cmake --build build --target install

RUN git clone --depth 1 https://github.com/rxseger/rx_tools.git &&\
    cd rx_tools &&\
    cmake -B build -DCMAKE_INSTALL_PREFIX=/target/usr -DCMAKE_BUILD_TYPE=Release &&\
    cmake --build build --target install

# Compile and install pcmcat and tune from KA9Q-Radio
ADD https://github.com/ka9q/ka9q-radio/archive/$KA9Q_REF.zip /tmp/ka9q-radio.zip
RUN unzip /tmp/ka9q-radio.zip -d /tmp && \
  cd /tmp/ka9q-radio-$KA9Q_REF && \
  make \
    -f Makefile.linux \
    ARCHOPTS= \
    pcmrecord tune && \
  mkdir -p /target/usr/bin/ && \
  cp pcmrecord /target/usr/bin/ && \
  cp tune /target/usr/bin/ && \
  rm -rf /root/ka9q-radio

COPY scripts/* /target/usr/bin/

# to support arm wheels
# RUN echo '[global]\nextra-index-url=https://www.piwheels.org/simple' > /target/etc/pip.conf

FROM debian:bookworm-slim AS prod
RUN apt-get -y update && apt-get -y upgrade && apt-get -y install --no-install-recommends \
    libusb-1.0-0 \
    python3-venv \
    python3-crcmod \
    python3-dateutil \
    python3-numpy \
    python3-requests \
    python3-pip \
    sox \
    bc \
    procps \
    rtl-sdr \
    libatlas3-base \
    avahi-utils \
    libnss-mdns \
    libbsd0 \
    soapysdr-module-all &&\
    rm -rf /var/lib/apt/lists/*

RUN pip install --break-system-packages --no-cache-dir --prefer-binary horusdemodlib

RUN sed -i -e 's/files dns/files mdns4_minimal [NOTFOUND=return] dns/g' /etc/nsswitch.conf

COPY --from=builder /target /
CMD ["bash"]
