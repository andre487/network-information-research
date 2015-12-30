"""
Aggregate data from stats.db
"""
import sqlite3

from collections import OrderedDict
from os import path
from functools import reduce

import jinja2
from ua_parser import user_agent_parser

PROJECT_DIR = path.dirname(__file__)
TEMPLATES_DIR = path.join(PROJECT_DIR, 'templates')
DB_FILE = path.join(PROJECT_DIR, 'data', 'stats.db')


def main():
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row

    hits_count = get_hits_count(db)
    stats_by_device = collect_api_by_device_stats(db)

    print_results(hits_count, stats_by_device)


def get_hits_count(db):
    cursor = db.execute('SELECT COUNT(*) AS count FROM stats')
    return cursor.fetchone()['count']


def collect_api_by_device_stats(db):
    cursor = db.execute("""
        SELECT
            connection_type,
            downlink_max,
            log_agent,
            api_supported
        FROM
            stats
        ORDER BY
            log_agent
    """)

    stats = OrderedDict((
        ('supported', set()),
        ('unsupported', set()),
        ('connection_types', set()),
        ('downlink_max', set()),
        ('data', OrderedDict())
    ))
    return reduce(handle_device_record, cursor, stats)


def handle_device_record(stats, row):
    stats_data = stats['data']
    device_data = user_agent_parser.Parse(row['log_agent'])

    os_key = device_data['os']['family']
    if device_data['os']['major']:
        os_key += ' {major}.{minor}'.format(**device_data['os'])

    ua_key = '{family} {major}.{minor}'.format(**device_data['user_agent'])
    merged_key = os_key + ' ' + ua_key

    if row['api_supported']:
        if os_key not in stats_data:
            stats_data[os_key] = OrderedDict()

        if ua_key not in stats_data[os_key]:
            stats_data[os_key][ua_key] = {
                'api_supported': 0,
                'connection_type': set(),
                'downlink_max': set()
            }

        stats['supported'].add(merged_key)
        stats['connection_types'].add(row['connection_type'])

        downlink_max = row['downlink_max']
        if downlink_max == -1:
            downlink_max = 'undefined'
        elif downlink_max == -2:
            downlink_max = 'infinity'

        stats['downlink_max'].add(downlink_max)

        stats_data[os_key][ua_key]['api_supported'] += row['api_supported']
        stats_data[os_key][ua_key]['connection_type'].add(row['connection_type'])
        stats_data[os_key][ua_key]['downlink_max'].add(downlink_max)

        return stats

    stats['unsupported'].add(merged_key)
    return stats


def print_results(hits_count, stats_by_device):
    tpl_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
            lstrip_blocks=True,
            trim_blocks=True
    )
    report = tpl_env.get_template('report.md').render(
            hits_count=hits_count,
            supported_count=len(stats_by_device['supported']),
            unsupported_count=len(stats_by_device['unsupported']),
            supported_items=stats_by_device['supported'],
            unsupported_items=stats_by_device['unsupported'],
            stats_by_device_data=stats_by_device['data'],
            connection_types=sorted(stats_by_device['connection_types']),
            downlink_max_values=sorted(stats_by_device['downlink_max']),
            detailed_stats=get_detailed_stats(stats_by_device)
    )
    print(report)


def get_detailed_stats(stats_by_device):
    detailed_stats = ''

    def add_report_details(line, indent=0):
        nonlocal detailed_stats
        detailed_stats += '\t' * indent + line + '\n'

    for os_key in stats_by_device['data']:
        add_report_details(os_key)

        os_data = stats_by_device['data'][os_key]
        for ua_key in os_data:
            ua_data = os_data[ua_key]
            add_report_details(ua_key, 1)

            for stat_name in ('api_supported', 'connection_type', 'downlink_max'):
                add_report_details(stat_name + ': ' + str(ua_data[stat_name]), 2)

    return detailed_stats.strip()


if __name__ == '__main__':
    main()
