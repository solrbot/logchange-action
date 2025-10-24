#!/bin/bash
set -e

# Install Python dependencies
pip install --no-cache-dir pyyaml requests

# Run the main Python script
python3 /action/src/main.py
