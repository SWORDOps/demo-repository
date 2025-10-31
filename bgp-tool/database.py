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

#def save_bgp_summary(data):
#    """Saves the BGP summary data to a file."""
#    with open('bgp_summary.json', 'w') as f:
        json.dump(data, f, indent=4)
#
#def load_bgp_summary():
#    """Loads the BGP summary data from a file."""
#    try:
#        with open('bgp_summary.json', 'r') as f:
#            return json.load(f)
#    except FileNotFoundError:
#        return None

#def get_latest_bgp_summary():
#    """This is a placeholder. In a real app, this would fetch from a database."""
#    return load_bgp_summary()

# In a production environment, the MongoDB connection string should be
# configured via an environment variable or a configuration file.
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "bgp_tool"

def get_db_connection():
    """Establishes a connection to the MongoDB server and returns the database object."""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db

def init_db():
    """Initializes the database and creates the necessary collections."""
    db = get_db_connection()

    # Create collections if they don't already exist.
    # MongoDB creates collections automatically on first insertion,
    # but we can create them explicitly here to be clear about our schema.
    if "bgp_summary" not in db.list_collection_names():
        db.create_collection("bgp_summary")

    if "hijack_alerts" not in db.list_collection_names():
        db.create_collection("hijack_alerts")

    if "bgp_flaps" not in db.list_collection_names():
        db.create_collection("bgp_flaps")

def get_latest_bgp_summary():
    """Returns the most recent BGP summary for each neighbor."""
    db = get_db_connection()
    return list(db.bgp_summary.aggregate([
        {'$sort': {'timestamp': -1}},
        {'$group': {
            '_id': '$neighbor',
            'doc': {'$first': '$$ROOT'}
        }},
        {'$replaceRoot': {'newRoot': '$doc'}}
    ]))

if __name__ == '__main__':
    # This allows us to initialize the database from the command line.
    init_db()
    print("Database initialized successfully.")
