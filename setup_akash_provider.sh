#!/bin/bash

# ==============================================================================
#
#          Akash Provider Setup Script
#
#  This script automates the setup of an Akash provider on a fresh
#  Ubuntu/Debian-based system. It installs all necessary prerequisites
#  and configures the Akash provider software.
#
#  Official Documentation:
#  https://akash.network/docs/providers/build-a-cloud-provider/
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
print_info "Starting Akash Provider setup..."

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

# --- User Input ---
print_info "Collecting required information..."

# Use environment variables if they exist, otherwise prompt the user.
if [ -z "$AKASH_DOMAIN" ]; then
  read -p "Enter your domain name (e.g., provider.yourdomain.com): " AKASH_DOMAIN
  if [ -z "$AKASH_DOMAIN" ]; then
    print_error "Domain name cannot be empty."
  fi
fi

if [ -z "$AKASH_WALLET_ADDRESS" ]; then
  read -p "Enter your Akash wallet address (akash1...): " AKASH_WALLET_ADDRESS
  if [[ ! "$AKASH_WALLET_ADDRESS" =~ ^akash1[a-z0-9]{38}$ ]]; then
    print_error "Invalid Akash wallet address format."
  fi
fi

export AKASH_DOMAIN
export AKASH_WALLET_ADDRESS
export AKASH_PRICING_SCRIPT_URL="https://raw.githubusercontent.com/akash-network/pricing-script/main/types/akash.json"

# --- 1. System Update and Prerequisite Installation ---
print_info "Updating system and installing prerequisites (curl, git, etc.)..."
apt-get update
apt-get install -y curl git

# --- 2. Install k3s (Lightweight Kubernetes) ---
print_info "Installing k3s (a lightweight Kubernetes distribution)..."
curl -sfL https://get.k3s.io | sh -
print_info "k3s installed successfully."

# --- 3. Configure Kubernetes Environment ---
print_info "Configuring Kubernetes (kubectl)..."
mkdir -p "$HOME/.kube"
cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
chown "$(id -u):$(id -g)" "$HOME/.kube/config"
export KUBECONFIG="$HOME/.kube/config"
print_info "Kubernetes configured. You can now use 'kubectl'."

# --- 4. Install Helm (Kubernetes Package Manager) ---
print_info "Installing Helm..."
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
rm get_helm.sh
print_info "Helm installed successfully."

# --- 5. Add Akash Helm Repository ---
print_info "Adding Akash Helm repository..."
helm repo add akash https://akash-network.github.io/helm-charts
helm repo update
print_info "Akash Helm repository is ready."

# --- 6. Install Akash Provider ---
print_info "Installing the Akash Provider using Helm..."

# Create a namespace for the provider
kubectl create namespace akash-services || print_info "Namespace 'akash-services' already exists."

# Create the provider configuration values file (provider.yaml)
print_info "Creating provider configuration file (provider.yaml)..."
cat <<EOF > provider.yaml
domain: "$AKASH_DOMAIN"
wallet: "$AKASH_WALLET_ADDRESS"
pricing:
  script:
    url: "$AKASH_PRICING_SCRIPT_URL"
EOF

# Install the provider using the Helm chart
helm install akash-provider akash/provider -n akash-services -f provider.yaml

print_info "Akash provider installation has been initiated."
print_info "It may take a few minutes for all components to become fully operational."
print_info "To check the status, run: 'kubectl get pods -n akash-services'"

# --- 7. Post-Installation Instructions ---
echo ""
print_info "==================== ACTION REQUIRED ===================="
print_info "Your Akash Provider setup is almost complete. Please follow these manual steps:"
echo ""
print_info "1. CONFIGURE YOUR DNS:"
print_info "   - Get your provider's public IP address by running: 'curl ifconfig.me'"
print_info "   - In your domain registrar's DNS settings, create an 'A' record for '$AKASH_DOMAIN' pointing to that public IP address."
print_info "   - Create a CNAME record for '*.$AKASH_DOMAIN' pointing to '$AKASH_DOMAIN'."
echo ""
print_info "2. FUND YOUR PROVIDER WALLET:"
print_info "   - Your provider needs a small amount of AKT to be operational on the network."
print_info "   - Send at least 5 AKT to your provider wallet address: $AKASH_WALLET_ADDRESS"
echo ""
print_info "3. MONITOR YOUR PROVIDER:"
print_info "   - You can monitor your provider's status using the Akash provider console: https://provider-console.akash.network/"
print_info "   - You can also check logs by running: 'kubectl logs -f -n akash-services -l app.kubernetes.io/name=provider'"
echo ""
print_info "========================================================="
print_info "Setup script finished."