#!/bin/bash

#git clone --branch release/2.x  https://github.com/OpenVPN/easy-rsa.git
if [ ! -d "easy-rsa" ]
then
    echo "unable to checkout easy-rsa"
    exit 2
fi

cd ./easy-rsa/easy-rsa/2.0/
cp openssl-1.0.0.cnf openssl.cnf
source ./vars
./clean-all
export EASY_RSA="${EASY_RSA:-.}"
./pkitool  --initca

#build server and client certs
./pkitool  --server server
./pkitool client1
./pkitool client2
cp -R keys/ ../../../
cd ../../..
