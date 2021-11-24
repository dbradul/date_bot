import os


def reverse_readline(filename, buf_size=8192):
    """A generator that returns the lines of a file in reverse order"""
    with open(filename) as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            buffer = fh.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            lines = buffer.split('\n')
            # The first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # If the previous chunk starts right from the beginning of line
                # do not concat the segment to the last line of new chunk.
                # Instead, yield the segment first
                if buffer[-1] != '\n':
                    lines[-1] += segment
                else:
                    yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if lines[index]:
                    yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment


# ----------------------------------------------------------------------------------------------------------------------
# TODO: Fix code duplication

import os
import sqlite3
from pydantic import BaseModel
from typing import Optional

DB_FILEPATH = './docker/sender/date.db'


class GentlemanInfo(BaseModel):
    profile_id: Optional[int] = 0
    age_from: Optional[int] = 0
    age_to: Optional[int] = 0
    priority: Optional[int] = 0


def execute_query(query, args=()):
    db_path = os.path.join(os.getcwd(), DB_FILEPATH)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(query, args)
        conn.commit()
        records = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]

    return records


def get_gentleman_info_by_profile_id(profile_id):
    query = 'select profile_id, age_from, age_to, priority from gentleman_info where profile_id=?;'
    records = execute_query(query, (profile_id,))
    return GentlemanInfo(**records[0]) if records else None


def put_gentleman_info(gentleman_info):
    query = 'insert into gentleman_info (profile_id, age_from, age_to, priority) values (?, ?, ?, ?);'
    execute_query(query, tuple(gentleman_info.dict().values()))


def update_gentleman_info(profile_id, priority):
    query = 'update gentleman_info set priority = ? where profile_id = ?;'
    execute_query(query, (priority, profile_id))


def upsert_gentlemen_by_profile_id(profile_id):
    if get_gentleman_info_by_profile_id(profile_id):
        update_gentleman_info(profile_id, priority=1)
    else:
        gentleman_info = GentlemanInfo(profile_id=profile_id, priority=1)
        put_gentleman_info(gentleman_info)
