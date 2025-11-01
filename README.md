# BGP Active Defense Platform

This application is a comprehensive BGP monitoring and active defense platform. It is designed to monitor your network prefixes, detect BGP hijacks, and provide tools for manual and automated mitigation.

## Features

*   **Multi-Vantage Point Monitoring:** Monitors BGP announcements from multiple sources (RIPEstat and BGPView) to provide a comprehensive view of your prefixes' status.
*   **Policy-Based Automated Mitigation:** Allows you to define policies in `config.json` to automatically respond to specific types of hijacks.
*   **Advanced Analytics:** Provides a dashboard with insights into historical hijack activity, including trends and top offending ASNs.
*   **Threat Intelligence Integration:** Enriches hijack alerts with an abuse confidence score from AbuseIPDB by checking a sample IP address associated with the hijacking ASN. **Note:** The ASN-to-IP conversion is a placeholder for demonstration purposes.
*   **Dark-Themed UI:** A modern, easy-to-read dark theme for use in network operations centers.

## Requirements

*   Python 3.10+
*   A running MongoDB instance.

## Installation and Setup

1.  **Clone the repository.**
2.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure the application:**
    *   Copy the `.env.example` file to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file to add your router credentials, BGP ASN, your MongoDB connection URI, and (optionally) your AbuseIPDB API key.
    *   **Crucially, you must set the `MONGODB_URI` variable.** This is the connection string for your MongoDB instance (e.g., `mongodb://user:password@host:port/`).
4.  **Run the application:**
    ```bash
    python app.py
    ```
    The application will be available at `http://127.0.0.1:5000`.