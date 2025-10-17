# Dynamic Decentralized Compute Load Balancer (Single Script Edition)

This repository contains a single, self-contained bash script to deploy a compute provider on either **Akash Network** or **iExec**, dynamically switching based on which network's token is currently more valuable.

This script is designed for maximum portability and ease of use, removing the need for multiple files and Python dependencies.

## How It Works

The `dynamic_balancer.sh` script handles everything:

1.  **Prerequisite Checks:** It automatically checks for and installs necessary tools like `curl` and `jq`. It also verifies that it's being run as root on a supported `x86_64` architecture.
2.  **Profitability Oracle:** It calls the public CoinGecko API to get the current market prices of Akash's `AKT` and iExec's `RLC` tokens.
3.  **Decision Engine:** It compares the token prices to determine the most profitable network.
4.  **State Management:** It keeps track of the currently active network in a hidden file (`.current_network`) to avoid unnecessary work.
5.  **Setup & Teardown:** It contains all the logic to install prerequisites (like Docker and k3s) and configure, start, or stop the services for either network.

## How to Use

### Prerequisites

1.  **A dedicated `x86_64` machine:** A physical server or a VPS with a public IP address running a fresh **Ubuntu or Debian-based** OS.
2.  **For Akash:** A domain name and an Akash wallet address.
3.  **For iExec:** An iExec wallet. You must create a `worker_wallet.json` file in the same directory as the script. You will also need Node.js/npm to install the `iexec` CLI for this.

### Execution

1.  **Download the script:**
    ```bash
    curl -o dynamic_balancer.sh https://raw.githubusercontent.com/your-username/your-repo-name/main/dynamic_balancer.sh
    ```
    *(Note: Replace the URL with the actual raw file URL once committed.)*

2.  **Make the script executable:**
    ```bash
    chmod +x dynamic_balancer.sh
    ```

3.  **(For iExec) Create your wallet file:**
    If you plan to use iExec, install their CLI and create the wallet file first.
    ```bash
    npm install -g iexec
    iexec wallet create
    ```
    Make sure to fund this wallet and deposit RLC for staking as per the iExec documentation.

4.  **Run the balancer:**
    Execute the script with `sudo`. It will guide you through the rest.
    ```bash
    sudo ./dynamic_balancer.sh
    ```
    The script will check profitability and, if a switch is needed, will prompt you for the necessary information (domain names, wallet addresses, passwords, etc.) to configure the new provider.

## Disclaimer

This is a proof-of-concept for educational and demonstration purposes. The profitability logic is simplistic and does not account for many real-world factors. Use at your own risk.