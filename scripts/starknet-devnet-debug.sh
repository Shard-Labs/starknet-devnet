#!/bin/bash
set -e
FLASK_APP=starknet_devnet.server FLASK_DEBUG=1 flask run --port 5050
