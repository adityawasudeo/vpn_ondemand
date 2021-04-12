FROM ubuntu:xenial as base

RUN apt-get update && apt-get install -y \
    net-tools \
    curl \
    git \
    vim \
    iputils-ping \
    openvpn \
    iptables
COPY vpn/server.conf /server.conf
COPY vpn/startVPN.sh /startVPN.sh
RUN chmod 744 /startVPN.sh
RUN mkdir /keys
COPY keys/keys/ca.crt /keys
COPY keys/keys/dh2048.pem /keys
COPY /keys/keys/server.crt /keys
COPY /keys/keys/server.key /keys
