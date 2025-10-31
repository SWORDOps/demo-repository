from pymongo import MongoClient
import os

def get_db_connection():
    """
    Establishes a connection to the MongoDB database using a connection
    string from an environment variable.
    """
    # Get the MongoDB connection string from the environment variable
    # Default to a local instance if not set, for convenience
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")

    client = MongoClient(uri)
    db = client.bgp_monitoring
    return db

# The functions below are for the old file-based approach and are no longer used.
# They are kept here for historical reference but can be removed.

def save_bgp_summary(data):
    """Saves the BGP summary data to a file."""
    with open('bgp_summary.json', 'w') as f:
        json.dump(data, f, indent=4)

def load_bgp_summary():
    """Loads the BGP summary data from a file."""
    try:
        with open('bgp_summary.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_latest_bgp_summary():
    """This is a placeholder. In a real app, this would fetch from a database."""
    return load_bgp_summary()