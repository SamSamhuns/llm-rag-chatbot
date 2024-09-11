"""
pymongo api function wrappers
"""
import os
from pymongo import MongoClient
from utils.common import timeit_decorator

DEBUG: bool = os.environ.get("DEBUG", "") != "False"


def user_exists_in_mongo(
        mongodb_client: MongoClient,
        user_id: str,
        database: str,
        collection: str,
        user_id_key: str = "_id"):
    """
    Check if user with id user_id exists in mongodb database and collection
    """
    users = mongodb_client[database][collection]
    user_exists = users.find_one({user_id_key: user_id})
    return bool(user_exists)


# if DEBUG is true, function runs are time
if DEBUG:
    user_exists_in_mongo = timeit_decorator(user_exists_in_mongo)
