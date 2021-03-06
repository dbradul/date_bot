import os
import sqlite3

from models import GentlemanInfo
from models import LadyInfo

DB_FILEPATH = './date.db'


def execute_query(query, args=()):
    db_path = os.path.join(os.getcwd(), DB_FILEPATH)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(query, args)
        conn.commit()
        records = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]

    return records


def get_gentleman_info():
    query = 'select profile_id, age_from, age_to, priority, deleted from gentleman_info;'
    records = execute_query(query)
    return {record['profile_id']: GentlemanInfo(**record) for record in records}


def get_gentleman_info_by_profile_id(profile_id):
    query = 'select profile_id, age_from, age_to, priority, deleted from gentleman_info where profile_id=?;'
    records = execute_query(query, (profile_id,))
    return GentlemanInfo(**records[0]) if records else None


def get_gentlemen_by_filter(priority, age_from, age_to, deleted):
    query = '''
        select 
            profile_id, age_from, age_to, priority 
        from 
            gentleman_info
        where
            priority = ? and 
            (age_from <=? or age_from is NULL or age_from = 0) and 
            (age_to >= ? or age_to is NULL or age_to = 0) and 
            (deleted = ? or deleted is NULL)
        ;
    '''
    records = execute_query(query, (priority, age_from, age_to, deleted))
    return [GentlemanInfo(**record) for record in records] if records else None


def put_gentleman_info(gentleman_info):
    query = 'insert into gentleman_info (profile_id, age_from, age_to, priority, deleted) values (?, ?, ?, ?, ?);'
    execute_query(query, tuple(gentleman_info.dict().values()))


def update_gentleman_info(gentleman_info):
    query = 'update gentleman_info set profile_id=?, age_from=?, age_to=?, priority=?, deleted=? where profile_id = ?;'
    execute_query(query, tuple(gentleman_info.dict().values()) + (gentleman_info.profile_id,))


def upsert_gentlemen_by_profile_id(gentleman_info):
    if get_gentleman_info_by_profile_id(gentleman_info.profile_id):
        update_gentleman_info(gentleman_info)
    else:
        gentleman_info = GentlemanInfo(profile_id=gentleman_info.profile_id)
        put_gentleman_info(gentleman_info)


# ----------------------------------------------------------------------------------------------------------------------
def get_lady_info_by_profile_id(profile_id):
    query = 'select profile_id, age from lady_info where profile_id=?;'
    records = execute_query(query, (profile_id,))
    return LadyInfo(**records[0]) if records else None


def put_lady_info(lady_info):
    query = 'insert into lady_info (profile_id, age) values (?, ?);'
    execute_query(query, tuple(lady_info.dict().values()))
