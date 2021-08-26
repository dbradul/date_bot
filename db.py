import json
import os
import sqlite3

from models import GentlemanInfo


def execute_query(query, args=()):
    db_path = os.path.join(os.getcwd(), 'date.db')
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(query, args)
        conn.commit()
        records = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]

    return records


def get_gentleman_info():
    query = 'select profile_id, age_from, age_to from gentleman_info;'
    records = execute_query(query)
    return {record['profile_id']: GentlemanInfo(**record) for record in records}


def get_gentleman_info_by_profile_id(profile_id):
    query = 'select profile_id, age_from, age_to from gentleman_info where profile_id=?;'
    records = execute_query(query, (profile_id,))
    return GentlemanInfo(**records[0]) if records else None


def put_gentleman_info(gentleman_info):
    query = 'insert into gentleman_info (profile_id, age_from, age_to) values (?, ?, ?);'
    execute_query(query, tuple(gentleman_info.dict().values()))


#
# result = get_gentleman_info()
# put_gentleman_info(
#     [
#         {'profile_id': 4445, 'age_from': 25, 'age_to': 50},
#         {'profile_id': 4443, 'age_from': 19, 'age_to': 91},
#     ]
# )
# print(result)
