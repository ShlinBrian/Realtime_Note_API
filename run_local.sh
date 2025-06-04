#!/bin/bash

# Function to print colored messages
print_message() {
  echo -e "\033[0;32m[Realtime Notes API]\033[0m $1"
}

print_warning() {
  echo -e "\033[1;33m[Warning]\033[0m $1"
}

print_error() {
  echo -e "\033[0;31m[Error]\033[0m $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  print_error "Docker is not installed. Please install Docker first."
  exit 1
fi

# Determine Docker Compose command
if ! docker compose version &> /dev/null; then
  print_warning "Docker Compose V2 not detected. Falling back to docker-compose."
  DOCKER_COMPOSE="docker-compose"
else
  DOCKER_COMPOSE="docker compose"
fi

# Parse command line arguments
COMMAND=${1:-"start"}

case $COMMAND in
  "start")
    print_message "Starting Realtime Notes API services..."
    $DOCKER_COMPOSE up -d
    print_message "Services are starting. Check logs with: ./run_local.sh logs"
    print_message "API will be available at: http://localhost:8000/docs"
    ;;
    
  "stop")
    print_message "Stopping all services..."
    $DOCKER_COMPOSE down
    ;;
    
  "logs")
    print_message "Showing logs (press Ctrl+C to exit)..."
    $DOCKER_COMPOSE logs -f
    ;;
    
  "clean")
    print_message "Stopping services and removing volumes..."
    $DOCKER_COMPOSE down -v
    if [ -f "local_api_key.txt" ]; then
      rm local_api_key.txt
    fi
    print_message "Cleanup complete."
    ;;
    
  "key")
    if [ -f "local_api_key.txt" ]; then
      API_KEY=$(grep -oP 'API_KEY=\K.*' local_api_key.txt)
      print_message "API Key: $API_KEY"
    else
      print_error "API key file not found. Services might still be starting up."
      print_message "Check logs with: ./run_local.sh logs"
    fi
    ;;
    
  *)
    print_message "Usage: ./run_local.sh [command]"
    echo "Commands:"
    echo "  start   - Start all services (default)"
    echo "  stop    - Stop all services"
    echo "  logs    - Show logs from all services"
    echo "  clean   - Stop services and remove volumes"
    echo "  key     - Display the API key"
    ;;
esac 