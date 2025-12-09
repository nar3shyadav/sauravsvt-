from flask import current_app, g
from pymongo import MongoClient

def get_db():
    """
    Configuration method to return db instance
    """
    if 'db' not in g:
        # Get the MongoDB URI from the application configuration
        mongo_uri = current_app.config['MONGO_URI']
        g.db = MongoClient(mongo_uri)[current_app.config['DB_NAME']]
    return g.db

def close_db(e=None):
    """
    Closes the database again at the end of the request.
    """
    db = g.pop('db', None)
    if db is not None:
        # By standard, PyMongo's client manages connections in the background.
        # This function is here for conceptual completion and can be extended
        # if specific cleanup is needed.
        pass
