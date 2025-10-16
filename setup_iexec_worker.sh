#!/bin/bash

# ==============================================================================
#
#          iExec Worker Setup Script
#
#  This script automates the setup of an iExec worker on a fresh
#  Ubuntu/Debian-based system. It installs Docker and Docker Compose,
#  and configures the iExec worker.
#
#  Based on the official documentation and repository:
#  https://github.com/iExecBlockchainComputing/wpwp-worker-setup
#
# ==============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Helper Functions ---
print_info() {
    echo "INFO: $1"
}

print_error() {
    echo "ERROR: $1" >&2
    exit 1
}

# --- Pre-flight Checks ---
print_info "Starting iExec Worker setup..."

# Check architecture
ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
    print_error "Unsupported architecture: $ARCH. This script currently only supports x86_64."
fi
print_info "Verified supported architecture: $ARCH"

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
  print_error "This script must be run as root. Please use 'sudo'."
fi

# --- 1. System Update and Prerequisite Installation ---
print_info "Updating system and installing prerequisites (curl, git, etc.)..."
apt-get update
apt-get install -y curl git

# --- 2. Install Docker and Docker Compose ---
print_info "Installing Docker Engine..."
if ! command -v docker &> /dev/null
then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    print_info "Docker installed successfully."
else
    print_info "Docker is already installed."
fi

print_info "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null
then
    LATEST_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    curl -L "https://github.com/docker/compose/releases/download/${LATEST_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    print_info "Docker Compose installed successfully."
else
    print_info "Docker Compose is already installed."
fi


# --- 3. User Input ---
print_info "Collecting required information..."

if [ -z "$WORKERPOOL_HOST" ]; then
  read -p "Enter the workerpool host address (e.g., workerpool.workerpass.iex.ec): " WORKERPOOL_HOST
  if [ -z "$WORKERPOOL_HOST" ]; then
    print_error "Workerpool host cannot be empty."
  fi
fi

if [ -z "$WALLET_PASSWORD" ]; then
  read -s -p "Enter the password for your iExec wallet file: " WALLET_PASSWORD
  echo
  if [ -z "$WALLET_PASSWORD" ]; then
    print_error "Wallet password cannot be empty."
  fi
fi

# --- 4. Create Wallet and Docker Compose files ---
print_info "Creating iExec worker configuration..."

# Check for wallet file
WALLET_FILE="worker_wallet.json"
if [ ! -f "$WALLET_FILE" ]; then
    print_error "Wallet file '$WALLET_FILE' not found in the current directory. Please create it first using 'iexec wallet create'."
fi

# Create docker-compose.yml
cat <<EOF > docker-compose.yml
version: '3.6'
networks:
  worker-net:
    name: worker-net
services:
  worker:
    image: iexechub/iexec-worker:7.2.0
    container_name: iexec-worker
    environment:
      - IEXEC_CORE_HOST=${WORKERPOOL_HOST}
      - IEXEC_CORE_PORT=443
      - IEXEC_CORE_PROTOCOL=https
      - IEXEC_WORKER_WALLET_PATH=/${WALLET_FILE}
      - IEXEC_WORKER_WALLET_PASSWORD=${WALLET_PASSWORD}
      - IEXEC_WORKER_NAME=My_Dynamic_Worker
      - IEXEC_WORKER_BASE_DIR=/iexec_out
      - IEXEC_WORKER_DOCKER_NETWORK_NAME=worker-net
      - IEXEC_WORKER_OVERRIDE_BLOCKCHAIN_NODE_ADDRESS=https://bellecour.iex.ec
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./iexec_out:/iexec_out
      - ./${WALLET_FILE}:/${WALLET_FILE}:ro
    restart: unless-stopped
    networks:
      - worker-net
EOF

print_info "docker-compose.yml created successfully."

# --- 5. Start the iExec Worker ---
print_info "Starting the iExec worker..."
docker-compose up -d

print_info "iExec worker has been started in the background."
print_info "To see the logs, run: 'docker-compose logs -f'"

# --- 6. Post-Installation Instructions ---
echo ""
print_info "==================== ACTION REQUIRED ===================="
print_info "Your iExec Worker setup is almost complete. Please remember:"
echo ""
print_info "1. CREATE AND FUND YOUR WALLET:"
print_info "   - If you haven't already, install the iExec CLI: 'npm install -g iexec'"
print_info "   - Create a wallet: 'iexec wallet create' (this will create ${WALLET_FILE})"
print_info "   - Fund this wallet with some ETH for gas on the Goerli testnet, and some RLC."
echo ""
print_info "2. STAKE YOUR RLC:"
print_info "   - You must deposit RLC into your iExec account to stake for tasks."
print_info "   - Run: 'iexec account deposit <amount> RLC'"
echo ""
print_info "3. MONITOR YOUR WORKER:"
print_info "   - You can monitor your worker's activity via the iExec Explorer."
echo ""
print_info "========================================================="
print_info "Setup script finished."