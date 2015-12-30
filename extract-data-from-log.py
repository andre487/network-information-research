"""
Extract data from stats.log and write to SQLite
"""
import re
import sqlite3

from functools import reduce
from os import path
from urllib import parse as urllib_parse

PROJECT_DIR = path.dirname(__file__)
LOG_FILE = path.join(PROJECT_DIR, 'data', 'stats.log')
DB_FILE = path.join(PROJECT_DIR, 'data', 'stats.db')

log_pattern = re.compile(
        '(?P<ip>[.:0-9a-fA-F]+) '
        '- - '
        '\[(?P<time>.*?)\] '
        '"(?P<method>GET) (?P<query>.*?) HTTP/1.\d" '
        '(?P<status_code>\d+) '
        '\d+ '
        '"(?P<referrer>.*?)" '
        '"(?P<user_agent>.*?)"'
)


def main():
    db = sqlite3.connect(DB_FILE)
    setup_stats_table(db)

    table = extract_table(open(LOG_FILE))
    insert_data(db, table)


def setup_stats_table(db):
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            time DATETIME,
            ip TEXT,
            status_code INTEGER,
            log_agent TEXT,
            stat_agent TEXT,
            referrer TEXT,
            `query` TEXT,
            event_type TEXT,
            api_supported BOOLEAN,
            connection_type TEXT,
            session_id TEXT,
            downlink_max NUMERIC,
            device_model TEXT,

            CONSTRAINT id PRIMARY KEY (time, ip)
        );
    """)

    db.commit()


def extract_table(fd):
    for line_data in (parse_line(line) for line in fd):
        if line_data:
            yield line_data


def parse_line(line):
    matches = log_pattern.match(line)
    if not matches:
        raise Exception('Line does not match the pattern:\n' + line)

    result = matches.groupdict()
    if not result['query'].startswith('/stat'):
        return

    result.update({
        'status_code': int(result['status_code']),
        'stat_data': parse_stat_data(result)
    })
    return result


def parse_stat_data(row):
    url_data = urllib_parse.urlparse(row['query'])
    if not url_data:
        raise Exception('Invalid URI:\n' + row['query'])

    query_chunks = url_data.query.split('&')
    params = reduce(add_query_param, query_chunks, {})

    if 'data' not in params:
        raise Exception('Data not in params:\n' + url_data.query)
    params['data'] = parse_stat_param(params['data'])

    return params


def add_query_param(result, param_str):
    if param_str:
        data = param_str.split('=')
        result.update([data])
    return result


def parse_stat_param(data_str):
    data_chunks = data_str.split(',')
    params = (param_str.split(':') for param_str in data_chunks)
    return dict(unquote_pair(p) for p in params)


def unquote_pair(pair):
    return (urllib_parse.unquote(item) for item in pair)


def insert_data(db, table):
    query = 'INSERT INTO stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    db.executemany(query, table_to_sequence(table))
    db.commit()


def table_to_sequence(table):
    for row in table:
        stat_data = row['stat_data']
        stat_parsed_data = stat_data['data']

        device_model = stat_parsed_data['devicemodel'] if 'devicemodel' in stat_parsed_data else 'not specified'
        api_supported = stat_parsed_data['connection-api-supported'] == 'true'

        yield (
            row['time'],
            row['ip'],
            row['status_code'],
            row['user_agent'],
            stat_parsed_data['user-agent'],
            row['referrer'],
            row['query'],
            stat_data['type'],
            api_supported,
            stat_parsed_data['connection-type'],
            stat_parsed_data['sessionid'],
            cast_downlink_max(stat_parsed_data['downlink-max']),
            device_model
        )


def cast_downlink_max(str_downlink_max):
    if str_downlink_max == 'undefined':
        return -1

    if str_downlink_max == 'infinity':
        return -2

    return float(str_downlink_max)


if __name__ == '__main__':
    main()
