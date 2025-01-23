from pymongo import MongoClient
from django.conf import settings
import datetime
import logging

logger = logging.getLogger(__name__)

def get_db():
    """
    Returns a connection to the MongoDB database
    """
    try:
        # Use a connection string that explicitly specifies the database
        client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[settings.MONGODB_NAME]
        # Test the connection
        client.server_info()
        logger.info(f"Successfully connected to MongoDB database: {settings.MONGODB_NAME}")
        return db
    except Exception as e:
        logger.error(f"MongoDB Connection Error: {str(e)}")
        raise 