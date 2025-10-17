# BGP Monitoring and Re-routing Tool

This web application provides a foundational platform for monitoring and managing BGP routes on a Cisco IOS router. It includes both direct router monitoring and public BGP monitoring for hijack detection.

## Features

- **BGP Summary Dashboard:** Displays a near real-time view of the BGP session summary from your router.
- **BGP Hijack Alerts:** Monitors public BGP data from the RIPEstat API and displays alerts for potential hijacks.
- **Manual Command Execution:** Allows for manual advertising and withdrawing of BGP routes through a user-friendly web form.
- **One-Click Mitigation:** Provides "Mitigate" and "Withdraw" buttons to automatically announce and withdraw more-specific prefixes to counter detected hijacks.
- **Background Monitoring:** Background processes periodically connect to the router and the RIPEstat API to fetch the latest BGP status and hijack alerts.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>/bgp-tool
    ```

2.  **Install dependencies:**
    Make sure you have Python 3 installed.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the `bgp-tool` directory and add the following, filling in your router's details:
    ```
    ROUTER_IP=your_router_ip
    ROUTER_USER=your_username
    ROUTER_PASSWORD=your_password
    BGP_ASN=your_asn
    ```
    **Note:** The `.env` file is included in `.gitignore` and will not be committed to the repository.

4.  **Run the application:**
    ```bash
    python app.py
    ```
    The application will be available at `http://127.0.0.1:5000`.

## How to Use

1.  Open your web browser and navigate to `http://127.0.0.1:5000`.
2.  The main page will display any detected BGP hijack alerts and the BGP summary from your router. This will automatically refresh every 5 minutes.
3.  To manually advertise or withdraw a route, fill out the form at the top of the page and click "Execute".
4.  To mitigate a detected hijack, click the "Mitigate" button next to the alert. This will automatically announce more-specific prefixes to reclaim your traffic.
5.  To withdraw a mitigation, click the "Withdraw" button next to the alert. This will automatically withdraw the more-specific prefixes that were announced during mitigation.

## Future Development

This application is a functional BGP monitoring and defense tool. Future development could include:
- Integration with a database for historical data logging and analysis.
- Integration with other public BGP data sources for improved redundancy and coverage.
- More advanced alerting and notification options (e.g., email, Slack).