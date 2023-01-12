FROM debian:bullseye
MAINTAINER sa2kng <knegge@gmail.com>
ARG HOMEDIR=/home/pi/horusdemodlib
ENV PATH=${PATH}:${HOMEDIR}

RUN apt-get -y update && apt -y upgrade && apt-get -y install --no-install-recommends cmake build-essential libusb-1.0-0-dev git python3-venv python3-crcmod python3-requests python3-pip sox bc rtl-sdr libatlas-base-dev rtl-sdr && rm -rf /var/lib/apt/lists/*

COPY . ${HOMEDIR}
WORKDIR ${HOMEDIR}

RUN cmake -B build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release &&\
    cmake --build build --target install
RUN echo '[global]\nextra-index-url=https://www.piwheels.org/simple' > /etc/pip.conf &&\
    python3 -m venv venv &&\
    . venv/bin/activate &&\
    pip install --no-cache-dir --prefer-binary -r requirements.txt &&\
    pip install --no-cache-dir --prefer-binary horusdemodlib

CMD ["bash"]
