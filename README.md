# BGP Re-routing Tool

This web application provides a user-friendly interface to advertise or withdraw BGP routes on a Cisco IOS router.

## Features

- **Web-based UI:** No need to use the command line for simple BGP route changes.
- **Advertise & Withdraw:** Easily add or remove network advertisements.
- **Direct Router Interaction:** Uses Netmiko to send commands directly to your router via SSH.

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

3.  **Configure Credentials (Optional but Recommended):**
    For security, you can store your router's username and password in a `.env` file. The application will automatically use them if the form fields are left blank.

    Create a `.env` file in the root of the project and add the following:
    ```
    ROUTER_USER=your_username
    ROUTER_PASSWORD=your_password
    ```
    **Note:** The `.env` file is included in `.gitignore` and will not be committed to the repository.

4.  **Run the application:**
    ```bash
    python app.py
    ```
    The application will be available at `http://127.0.0.1:5000`.

## How to Use

1.  Open your web browser and navigate to `http://127.0.0.1:5000`.
2.  Fill out the form with your router's information:
    -   **Router IP/Hostname:** The address of your Cisco router.
    -   **Username & Password:** Your SSH credentials.
    -   **BGP ASN:** Your Autonomous System Number.
    -   **Neighbor IP:** The IP of your BGP peer.
    -   **Prefix to Advertise/Withdraw:** The network in CIDR notation (e.g., `192.0.2.0/24`).
    -   **Action:** Choose to "Advertise" or "Withdraw" the route.
3.  Click **Execute**.
4.  The output from the router will be displayed on the page.