# Dynamic Decentralized Compute Load Balancer

This project provides a proof-of-concept for a dynamic load balancer that can allocate your compute resources to the most profitable decentralized network. It currently supports switching between **Akash Network** and **iExec**.

## How It Works

The system is composed of three main parts:

1.  **Setup Scripts (`setup_akash_provider.sh`, `setup_iexec_worker.sh`):** These bash scripts handle the automated setup and deployment of a provider node on either Akash or iExec. They install all necessary prerequisites and configure the services.
2.  **Profitability Oracle (`get_profitability.py`):** A simple Python script that fetches the current market price of Akash's `AKT` token and iExec's `RLC` token from the public CoinGecko API.
3.  **Core Switching Logic (`main.py`):** The main control script. It runs the oracle to get the latest prices, decides which network is currently more profitable, and then orchestrates the switch by tearing down the old service and bringing up the new one.

The system maintains its current state in a hidden file (`.current_network`) to know which network is currently active.

## Architecture Support

**This entire stack only supports the `x86_64` (also known as `amd64`) architecture.**

This is a limitation of the underlying provider software for both Akash and iExec. The setup scripts will automatically check your system's architecture and exit if it is not `x86_64`.

## How to Use

### Prerequisites

1.  **A dedicated `x86_64` machine:** A physical server or a VPS with a public IP address running a fresh **Ubuntu or Debian-based** OS.
2.  **A domain name:** Required for the Akash provider.
3.  **An Akash Wallet:** With `AKT` tokens.
4.  **An iExec Wallet:** With `RLC` tokens. You will need to create a `worker_wallet.json` file in the project directory using the `iexec` CLI.
5.  **Node.js and npm:** Required for the `iexec` CLI.

### Initial Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Make the setup scripts executable:**
    ```bash
    chmod +x setup_*.sh
    ```

3.  **Install the iExec CLI:**
    ```bash
    npm install -g iexec
    ```

4.  **Create your iExec wallet file:**
    This will create the `worker_wallet.json` file that the iExec setup script needs.
    ```bash
    iexec wallet create
    ```
    Make sure to fund this wallet and deposit RLC for staking as per the iExec documentation.

### Running the Load Balancer

To run a cycle of the load balancer, execute the main script:

```bash
python3 main.py
```

The script will:
1.  Fetch the latest token prices.
2.  Determine the most profitable network.
3.  Check if a switch is necessary.
4.  If a switch is needed, it will call the appropriate teardown and setup scripts. **You will need to be present to enter `sudo` passwords and any other information prompted by the setup scripts.**

## Disclaimer

This is a proof-of-concept and not a production-ready system. The profitability logic is extremely simple (it just compares token prices) and does not account for many real-world factors like network demand, transaction fees, or provider costs. It is intended for educational and demonstration purposes. Always do your own research.