#!/bin/bash

# Get the directory where this script is located
dname=$(dirname ${BASH_SOURCE[0]})

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <server_name> <port>"
    exit 1
fi

# Run the client with the provided server name and port
python3 $dname/client.py $1 $2