#!/bin/bash
mkdir -p /dev/net
mknod /dev/net/tun c 10 200

#iptables -t nat -A POSTROUTING -s 10.250.0.0/24 -o eth0 -j MASQUERADE

iptables -I FORWARD -i tun0 -o eth0 -s 10.8.0.0/24 -m conntrack --ctstate NEW -j ACCEPT
iptables -I FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o eth0 -j MASQUERADE

openvpn --config /server.conf
