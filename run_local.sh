#!/bin/bash

# Simple helper script for Docker operations

case ${1:-"help"} in
  "logs")
    docker compose logs -f
    ;;
    
  "key")
    if [ -f "local_api_key.txt" ]; then
      grep -oP 'API_KEY=\K.*' local_api_key.txt
    else
      echo "API key not found. Run 'make run' first."
    fi
    ;;
    
  *)
    echo "Usage: ./run_local.sh [logs|key]"
    echo "  logs - Show Docker logs"
    echo "  key  - Show API key"
    echo ""
    echo "To start/stop services, use:"
    echo "  make run   - Start services"
    echo "  make clean - Stop and clean"
    ;;
esac