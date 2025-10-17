#!/bin/bash

# ==============================================================================
#
#       Dynamic Decentralized Compute Load Balancer - Single Script Edition
#
# This single script automates the process of deploying a compute provider on
# either Akash Network or iExec, based on which network's token is currently
# more valuable. It is designed for portability and ease of use.
#
# ==============================================================================

# --- Script Configuration & Setup ---
set -e # Exit immediately if a command exits with a non-zero status.

# File to store the currently active network
STATE_FILE=".current_network"

# --- Helper Functions ---
print_info() {
    echo "INFO: $1"
}

print_error() {
    echo "ERROR: $1" >&2
    exit 1
}

# --- Prerequisite Checks ---
check_prerequisites() {
    print_info "Performing pre-flight checks..."

    # 1. Check for root privileges
    if [ "$(id -u)" -ne 0 ]; then
      print_error "This script must be run as root. Please use 'sudo'."
    fi

    # 2. Check architecture
    ARCH=$(uname -m)
    if [ "$ARCH" != "x86_64" ]; then
        print_error "Unsupported architecture: $ARCH. This script currently only supports x86_64."
    fi
    print_info "Verified supported architecture: $ARCH"

    # 3. Check for essential tools (curl, jq)
    if ! command -v curl &> /dev/null || ! command -v jq &> /dev/null; then
        print_info "Installing prerequisites: curl and jq..."
        apt-get update
        apt-get install -y curl jq
        print_info "curl and jq installed successfully."
    else
        print_info "curl and jq are already installed."
    fi
}

# --- State Management ---
get_current_network() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "none"
    fi
}

set_current_network() {
    echo "$1" > "$STATE_FILE"
    print_info "Set current network to: $1"
}

# --- Profitability Oracle ---
get_prices() {
    print_info "Fetching profitability data from CoinGecko API..."
    local api_url="https://api.coingecko.com/api/v3/simple/price?ids=akash-network,rlc&vs_currencies=usd"

    local response
    response=$(curl -s "$api_url")

    if [ -z "$response" ] || ! echo "$response" | jq . > /dev/null 2>&1; then
        print_error "Failed to get valid JSON response from CoinGecko API."
        return 1
    fi

    echo "$response"
}

decide_most_profitable() {
    local prices_json=$1

    local akash_price
    akash_price=$(echo "$prices_json" | jq -r '."akash-network".usd // 0')

    local iexec_price
    iexec_price=$(echo "$prices_json" | jq -r '.rlc.usd // 0')

    print_info "Profitability check: Akash (AKT) = \$${akash_price}, iExec (RLC) = \$${iexec_price}"

    # bc is a command-line calculator, used here to compare floating point numbers
    if (( $(echo "$akash_price > $iexec_price" | bc -l) )); then
        echo "akash"
    else
        echo "iexec"
    fi
}

teardown_akash() {
    print_info "Tearing down Akash provider..."
    if command -v helm &> /dev/null && helm status akash-provider -n akash-services > /dev/null 2>&1; then
        helm uninstall akash-provider -n akash-services
        print_info "Akash provider successfully uninstalled."
    else
        print_info "Akash provider not found or Helm is not installed. Skipping teardown."
    fi
}

setup_akash() {
    print_info "--- Starting Akash Provider Setup ---"

    # 1. Install prerequisites (k3s and Helm)
    if ! command -v k3s &> /dev/null; then
        print_info "Installing k3s (a lightweight Kubernetes distribution)..."
        curl -sfL https://get.k3s.io | sh -
        print_info "k3s installed successfully."
    else
        print_info "k3s is already installed."
    fi

    if ! command -v helm &> /dev/null; then
        print_info "Installing Helm..."
        curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
        chmod 700 get_helm.sh
        ./get_helm.sh
        rm get_helm.sh
        print_info "Helm installed successfully."
    else
        print_info "Helm is already installed."
    fi

    # 2. Configure Kubernetes
    print_info "Configuring Kubernetes (kubectl)..."
    mkdir -p "$HOME/.kube"
    cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
    chown "$(id -u):$(id -g)" "$HOME/.kube/config"
    export KUBECONFIG="$HOME/.kube/config"
    print_info "Kubernetes configured."

    # 3. Add Akash Helm repository
    print_info "Adding Akash Helm repository..."
    helm repo add akash https://akash-network.github.io/helm-charts
    helm repo update
    print_info "Akash Helm repository is ready."

    # 4. Get user input
    local akash_domain
    read -p "Enter your domain name for the Akash provider (e.g., provider.yourdomain.com): " akash_domain
    if [ -z "$akash_domain" ]; then
        print_error "Domain name cannot be empty."
    fi

    local akash_wallet_address
    read -p "Enter your Akash wallet address (akash1...): " akash_wallet_address
    if [[ ! "$akash_wallet_address" =~ ^akash1[a-z0-9]{38}$ ]]; then
        print_error "Invalid Akash wallet address format."
    fi

    # 5. Install the Akash provider
    print_info "Installing the Akash Provider using Helm..."
    kubectl create namespace akash-services || print_info "Namespace 'akash-services' already exists."

    cat <<EOF > provider.yaml
domain: "$akash_domain"
wallet: "$akash_wallet_address"
pricing:
  script:
    url: "https://raw.githubusercontent.com/akash-network/pricing-script/main/types/akash.json"
EOF

    helm install akash-provider akash/provider -n akash-services -f provider.yaml
    print_info "Akash provider installation has been initiated."
    print_info "--- Akash Provider Setup Complete ---"
}

teardown_iexec() {
    print_info "Tearing down iExec worker..."
    if [ -f "docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
        docker-compose down
        print_info "iExec worker successfully stopped."
    else
        print_info "docker-compose.yml not found or Docker Compose is not installed. Skipping teardown."
    fi
}

setup_iexec() {
    print_info "--- Starting iExec Worker Setup ---"

    # 1. Install Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        print_info "Installing Docker Engine..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
        print_info "Docker installed successfully."
    else
        print_info "Docker is already installed."
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_info "Installing Docker Compose..."
        local latest_compose_version
        latest_compose_version=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        curl -L "https://github.com/docker/compose/releases/download/${latest_compose_version}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        print_info "Docker Compose installed successfully."
    else
        print_info "Docker Compose is already installed."
    fi

    # 2. Get user input
    local workerpool_host
    read -p "Enter the iExec workerpool host address (e.g., workerpool.workerpass.iex.ec): " workerpool_host
    if [ -z "$workerpool_host" ]; then
        print_error "Workerpool host cannot be empty."
    fi

    local wallet_password
    read -s -p "Enter the password for your iExec wallet file: " wallet_password
    echo
    if [ -z "$wallet_password" ]; then
        print_error "Wallet password cannot be empty."
    fi

    # 3. Create Wallet and Docker Compose files
    local wallet_file="worker_wallet.json"
    if [ ! -f "$wallet_file" ]; then
        print_error "Wallet file '$wallet_file' not found. Please create it first using 'iexec wallet create' and fund it."
    fi

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
      - IEXEC_CORE_HOST=${workerpool_host}
      - IEXEC_CORE_PORT=443
      - IEXEC_CORE_PROTOCOL=https
      - IEXEC_WORKER_WALLET_PATH=/${wallet_file}
      - IEXEC_WORKER_WALLET_PASSWORD=${wallet_password}
      - IEXEC_WORKER_NAME=My_Dynamic_Worker
      - IEXEC_WORKER_BASE_DIR=/iexec_out
      - IEXEC_WORKER_DOCKER_NETWORK_NAME=worker-net
      - IEXEC_WORKER_OVERRIDE_BLOCKCHAIN_NODE_ADDRESS=https://bellecour.iex.ec
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./iexec_out:/iexec_out
      - ./${wallet_file}:/${wallet_file}:ro
    restart: unless-stopped
    networks:
      - worker-net
EOF
    print_info "docker-compose.yml created successfully."

    # 4. Start the iExec Worker
    print_info "Starting the iExec worker..."
    docker-compose up -d
    print_info "iExec worker has been started in the background."
    print_info "--- iExec Worker Setup Complete ---"
}


# --- Main Logic ---
main() {
    check_prerequisites

    print_info "Starting Dynamic Compute Load Balancer..."

    local prices_json
    prices_json=$(get_prices)
    if [ -z "$prices_json" ]; then
        print_error "Could not fetch profitability data. Exiting."
    fi

    local target_network
    target_network=$(decide_most_profitable "$prices_json")
    print_info "Target network determined to be: $target_network"

    local current_network
    current_network=$(get_current_network)
    print_info "Current active network is: $current_network"

    if [ "$target_network" == "$current_network" ]; then
        print_info "Target network is already active. No changes needed. Exiting."
        exit 0
    fi

    print_info "Switching from '$current_network' to '$target_network'..."

    # Teardown the current network
    if [ "$current_network" == "akash" ]; then
        teardown_akash
    elif [ "$current_network" == "iexec" ]; then
        teardown_iexec
    fi

    # Setup the new target network
    if [ "$target_network" == "akash" ]; then
        setup_akash
    elif [ "$target_network" == "iexec" ]; then
        setup_iexec
    fi

    set_current_network "$target_network"
    print_info "Dynamic Compute Load Balancer run finished."
}

# --- Script Execution ---
main