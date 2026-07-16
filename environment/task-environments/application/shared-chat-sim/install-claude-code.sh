#!/bin/bash
set -euo pipefail

apt-get update
apt-get install -y curl python3 python3-pip git

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh

pip3 install pytest==8.4.1 pytest-json-ctrf==0.3.5
