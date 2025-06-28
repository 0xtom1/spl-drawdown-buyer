#!/bin/bash

# Exit on any error
set -e

# Check the MODE environment variable to decide which script to run
case "$MODE" in
  "BUYER")
    echo "Running BUYER..."
    python /app/spl_drawdown/main_buyer.py
    ;;
  "SELLER")
    echo "Running SELLER..."
    python /app/spl_drawdown/main_seller.py
    ;;
  *)
    echo "Error: MODE environment variable must be 'BUYER' or 'SELLER', got '$MODE'"
    exit 1
    ;;
esac