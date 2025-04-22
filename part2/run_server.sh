#!/bin/bash

dname=$(dirname ${BASH_SOURCE[0]})

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <server_name> <port>"
    exit 1
fi

python3 $dname/server.py $1 $2