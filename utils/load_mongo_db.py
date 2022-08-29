from decouple import config

DB_PASS = config('DB_PASS')
def get_database():
    from pymongo import MongoClient

    # Provide the mongodb atlas url to connect python to mongodb using pymongo
    CONNECTION_STRING = f"mongodb+srv://yc:{DB_PASS}@wordle-stats.8cl8bxu.mongodb.net/WordleStats"

    # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
    client = MongoClient(CONNECTION_STRING)

    # Create the database for our example (we will use the same database throughout the tutorial)
    return client['global_data']
    