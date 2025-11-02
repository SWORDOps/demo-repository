# BGP Active Defense Platform

This application is a comprehensive BGP monitoring and active defense platform. It is designed to monitor your network prefixes, detect BGP hijacks, and provide tools for manual and automated mitigation, as well as low-level hardware recovery.

## Features

### Network Monitoring & Defense
*   **Multi-Vantage Point Monitoring:** Monitors BGP announcements from multiple sources (RIPEstat and BGPView) to provide a comprehensive view of your prefixes' status.
*   **Policy-Based Automated Mitigation:** Allows you to define policies in `config.json` to automatically respond to specific types of hijacks.
*   **Advanced Analytics:** Provides a dashboard with insights into historical hijack activity, including trends and top offending ASNs.
*   **Threat Intelligence Integration:** Enriches hijack alerts with an abuse confidence score from AbuseIPDB by checking a sample IP address associated with the hijacking ASN.
*   **Dark-Themed UI:** A modern, easy-to-read dark theme for use in network operations centers.

### Hardware Recovery & Analysis (Advanced)
*   **Multi-Platform Support:** The integrated recovery script targets Cisco ISR, ASA, and generic MIPS devices.
*   **JTAG Exploitation:** Tools for dumping memory and flash.
*   **Firmware Analysis:** Automated filesystem analysis and bootloader scanning.
*   **ROMMON Recovery:** Automated password reset workflows.

## Installation and Setup

1.  **Clone the repository.**
2.  **Install the package:**
    This will install the `bgp-defense-tool` package and all its Python dependencies.
    ```bash
    pip install .
    ```
3.  **Configure the application:**
    *   Copy the `.env.example` file to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file to add your router credentials, BGP ASN, your MongoDB connection URI, and (optionally) your AbuseIPDB API key.
4.  **Run the application:**
    ```bash
    python run.py
    ```
    The application will be available at `http://127.0.0.1:5000`.

## Hardware Recovery Tool Dependencies

The hardware recovery script (`scripts/cisco_recovery.sh`) requires several external command-line tools to be installed on the system where it will be run. The "Hardware Recovery" page in the web UI includes a "Pre-flight Check" to help you verify which of these are present.

-   **Core:** `bash`, `stty`, `timeout`, `logger`, `lsusb`, `find`
-   **Analysis:** `strings`, `binwalk`, `hexdump`, `grep`, `awk`
-   **JTAG:** `openocd`
-   **Automation:** `expect`

### ⚠️ Disclaimer

The hardware recovery tool contains dangerous features, especially the JTAG memory write function. It can cause irreversible damage to the target device. The user assumes all responsibility for any actions performed by this script. **Use with extreme caution and only as root.**
