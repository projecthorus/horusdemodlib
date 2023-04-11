# Guide for running on docker

## Host system
This guide will assume an updated installation of Debian bullseye (11), it should work on a lot of different linux OS and architectures.<br>
You will need to install the libraries and supporting sw/fw for your sdr device, including udev rules and blacklists.<br>
Additional software such as soapysdr is not needed on the host, but can certainly be installed.<br>
```shell
sudo apt install rtl-sdr
echo "blacklist dvb_usb_rtl28xxu" | sudo tee /etc/modprobe.d/blacklist-rtlsdr.conf
sudo modprobe -r dvb_usb_rtl28xxu
```

See the [docker installation](#install-dockerio) at the bottom of this page.

## Building the image
If the docker image is not available, or you want to build from your own branch etc.
```shell
git clone https://github.com/projecthorus/horusdemodlib.git
cd horusdemodlib
docker-compose build
```

## Configuration

Start with creating a directory with a name representing the station, this will be shown in several places in the resulting stack.
```shell
mkdir -p projecthorus
cd projecthorus
wget https://raw.githubusercontent.com/projecthorus/horusdemodlib/master/docker-compose.yml
wget -O user.cfg https://raw.githubusercontent.com/projecthorus/horusdemodlib/master/user.cfg.example
wget -O user.env https://raw.githubusercontent.com/projecthorus/horusdemodlib/master/user.env.example
```

The file `user.env` contains all the station variables (earlier in each script), the DEMODSCRIPT is used by compose.<br>
The `user.cfg` sets the details sent to Sondehub.<br> 
Use your favourite editor to configure these:
```shell
nano user.env
nano user.cfg
```
Please note that the values in user.env should not be escaped with quotes or ticks.

## Bringing the stack up

The `docker-compose` (on some systems it's `docker compose` without the hyphen) is the program controlling the creation, updating, building and termination of the stack.
The basic commands you will use is `docker-compose up` and `docker-compose down`.
When you edit the compose file or configuration it will try to figure out what needs to be done to bring the stack in sync of what has changed.

Starting the stack in foreground (terminate with Ctrl-C):
```shell
docker-compose up
```

Starting the stack in background:
```shell
docker-compose up -d
```

Stopping the stack:
```shell
docker-compose down
```

Updating the images and bringing the stack up:
```shell
docker-compose pull
docker-compose up -d
```

Over time there will be old images accumulating, these can be removed with `docker image prune -af`

## Using SoapySDR with rx_tools

If you want to use other SDR than rtl_sdr, the docker build includes rx_tools.<br>
Select docker_soapy_single.sh and add the extra argument to select the sdr in SDR_EXTRA:
```shell
# Script name
DEMODSCRIPT="docker_soapy_single.sh"
SDR_EXTRA="-d driver=rtlsdr"
```

## Monitoring and maintenance

Inside each container, the logs are output to stdout, which makes them visible from outside the container in the logs.
Starting to monitor the running stack:
```shell
docker-compose logs -f
```

If you want to run commands inside the containers, this can be done with the following command:
````shell
docker-compose exec horusdemod bash
````
The container needs to be running. Exit with Ctrl-D or typing `exit`.

# Install Docker.io
(Or you can install Docker.com engine via the [convenience script](https://docs.docker.com/engine/install/debian/#install-using-the-convenience-script))

In Debian bullseye there's already a docker package, so installation is easy:
```shell
sudo apt install docker.io apparmor
sudo apt -t bullseye-backports install docker-compose
sudo adduser $(whoami) docker
```
Re-login for the group permission to take effect.

The reason for using backports is the version of compose in bullseye is 1.25 and lacks cgroup support, the backport is version 1.27
<br>If your dist doesn't have backports, enable with this, and try the installation of docker-compose again:
```shell
echo "deb http://deb.debian.org/debian bullseye-backports main contrib non-free" | sudo tee /etc/apt/sources.list.d/backports.list
suod apt-key adv --keyserver keyserver.ubuntu.com --recv-keys  648ACFD622F3D138 0E98404D386FA1D9
sudo apt update
```
If you cannot get a good compose version with your dist, please follow [the official guide](https://docs.docker.com/compose/install/linux/#install-the-plugin-manually).
