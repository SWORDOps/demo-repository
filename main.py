import subprocess
import json
import os
import sys

# --- Configuration ---
STATE_FILE = ".current_network"

# --- Helper Functions ---
def print_info(message):
    print(f"INFO: {message}")

def print_error(message):
    print(f"ERROR: {message}", file=sys.stderr)

def run_command(command, shell=False):
    """Executes a command and returns its output."""
    print_info(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            shell=shell
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}")
        print_error(f"Stderr: {e.stderr.strip()}")
        return None

def get_current_network():
    """Reads the currently active network from the state file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    return "none"

def set_current_network(network_name):
    """Writes the currently active network to the state file."""
    with open(STATE_FILE, "w") as f:
        f.write(network_name)
    print_info(f"Set current network to: {network_name}")

def decide_most_profitable(prices):
    """
    A simple decision engine. For this PoC, we just compare token prices.
    A real-world implementation would be much more complex, factoring in
    network demand, provider costs, etc.
    """
    akash_price = prices.get("akash", {}).get("price_usd", 0)
    iexec_price = prices.get("iexec", {}).get("price_usd", 0)

    print_info(f"Profitability check: Akash (AKT) = ${akash_price}, iExec (RLC) = ${iexec_price}")

    if akash_price > iexec_price:
        return "akash"
    # If iExec is more profitable or prices are equal, we default to it.
    return "iexec"

def teardown_akash():
    """Stops and removes the Akash provider services."""
    print_info("Tearing down Akash provider...")
    # Assuming k3s is used, stopping the helm deployment
    if run_command(["helm", "uninstall", "akash-provider", "-n", "akash-services"]) is not None:
        print_info("Akash provider successfully uninstalled.")
    else:
        print_error("Failed to uninstall Akash provider. It might not be running.")

def teardown_iexec():
    """Stops and removes the iExec worker container."""
    print_info("Tearing down iExec worker...")
    if os.path.exists("docker-compose.yml"):
        if run_command(["docker-compose", "down"]) is not None:
            print_info("iExec worker successfully stopped.")
        else:
            print_error("Failed to stop iExec worker.")
    else:
        print_info("docker-compose.yml not found, assuming iExec is not running.")


# --- Main Logic ---
def main():
    print_info("Starting Dynamic Compute Load Balancer...")

    # 1. Get profitability data
    print_info("Fetching profitability data...")
    # Ensure dependencies for the oracle are installed
    run_command(["pip", "install", "-r", "requirements.txt"])
    price_data_json = run_command([sys.executable, "get_profitability.py"])

    if not price_data_json:
        print_error("Could not fetch profitability data. Exiting.")
        sys.exit(1)

    prices = json.loads(price_data_json)

    # 2. Decide which network is most profitable
    target_network = decide_most_profitable(prices)
    print_info(f"Target network determined to be: {target_network}")

    # 3. Get current state
    current_network = get_current_network()
    print_info(f"Current active network is: {current_network}")

    # 4. Perform the switch if necessary
    if target_network == current_network:
        print_info("Target network is already active. No changes needed. Exiting.")
        sys.exit(0)

    print_info(f"Switching from '{current_network}' to '{target_network}'...")

    # Teardown the current network if it's not "none"
    if current_network == "akash":
        teardown_akash()
    elif current_network == "iexec":
        teardown_iexec()

    # Setup the new target network
    if target_network == "akash":
        print_info("Setting up Akash provider...")
        # Note: The setup script requires sudo and user interaction.
        # This orchestrator can only trigger it. The user must be present.
        print_info("Please follow the prompts from the setup script.")
        run_command(["sudo", "./setup_akash_provider.sh"], shell=True)
    elif target_network == "iexec":
        print_info("Setting up iExec worker...")
        print_info("Please follow the prompts from the setup script.")
        run_command(["sudo", "./setup_iexec_worker.sh"], shell=True)

    # 5. Update state
    set_current_network(target_network)
    print_info("Dynamic Compute Load Balancer run finished.")

if __name__ == "__main__":
    main()