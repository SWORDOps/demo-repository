from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os

def get_db_connection():
    """
    Establishes a connection to the MongoDB database using a connection
    string from an environment variable.
    """
    # Get the MongoDB connection string from the environment variable
    # Default to a local instance if not set, for convenience
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")

    # It's better to let the caller handle the exception
    # so they know the database connection failed.
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)

    # The ismaster command is cheap and does not require auth, used to check connection.
    client.admin.command('ismaster')

    db = client.bgp_monitoring
    return db