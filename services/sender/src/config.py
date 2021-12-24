import os
from pymongo import MongoClient

_client = MongoClient(
    host=os.environ.get('MONGO_HOST', 'mongo'),
    port=int(os.environ.get('MONGO_PORT', 27017))
)

_db = _client.main


def set(name, value, scope='main'):
    collection = _db[scope]
    query = {'name': name}
    data = {'name': name, 'value': value}
    # inserted_id = collection.insert_one(data).inserted_id
    raw_result = collection.replace_one(query, data, upsert=True).raw_result
    return raw_result


def get(name, scope='main'):
    collection = _db[scope]
    query = {'name': name}
    it = collection.find(query)
    if it:
        return it[0]['value']
    return None