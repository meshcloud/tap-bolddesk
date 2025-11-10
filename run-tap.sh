#!/bin/bash

# Simple wrapper script to run tap-bolddesk with poetry

CONFIG_FILE=".secrets/config.json"

# Check if poetry.lock exists and dependencies are installed
if [ ! -d ".venv" ] && [ ! -f "poetry.lock" ]; then
    echo "Installing dependencies..."
    poetry install
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    echo "Please create it and add your API credentials."
    exit 1
fi

# Pass all arguments through to tap-bolddesk with the config file
poetry run tap-bolddesk --config "$CONFIG_FILE" "$@"
