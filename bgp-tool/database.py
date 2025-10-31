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

    client = MongoClient(uri, serverSelectionTimeoutMS=5000) # Set a timeout
    try:
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
    except ConnectionFailure:
        print("Server not available")
        # You might want to return None or raise an exception here
        # For the app, we'll let the higher-level try/except handle it

    db = client.bgp_monitoring
    return db