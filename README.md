# BGP Monitoring and Re-routing Tool

This web application provides a foundational platform for monitoring and managing BGP routes on a Cisco IOS router.

## Features

- **BGP Summary Dashboard:** Displays a near real-time view of the BGP session summary from your router.
- **Manual Command Execution:** Allows for manual advertising and withdrawing of BGP routes through a user-friendly web form.
- **Background Monitoring:** A background process periodically connects to the router to fetch the latest BGP status.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    Make sure you have Python 3 installed.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the root of the project and add the following, filling in your router's details:
    ```
    ROUTER_IP=your_router_ip
    ROUTER_USER=your_username
    ROUTER_PASSWORD=your_password
    ```
    **Note:** The `.env` file is included in `.gitignore` and will not be committed to the repository. The `bgp_monitor.py` script requires these variables to be set to connect to your router.

4.  **Run the application:**
    ```bash
    python app.py
    ```
    The application will be available at `http://127.0.0.1:5000`.

## How to Use

1.  Open your web browser and navigate to `http://127.0.0.1:5000`.
2.  The main page will display the BGP summary from your router. This will automatically refresh every 5 minutes.
3.  To manually advertise or withdraw a route, fill out the form and click "Execute".
4.  The output from the router command will be displayed on the page.

## Future Development

This application is a foundational first step. Future development will focus on integrating public BGP data sources for hijack and route leak detection.