from pymongo import MongoClient

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