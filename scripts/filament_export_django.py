#!/usr/bin/env python3
"""Export a private, read-only Django SQLite backup for the one-time CMS move.

No Django installation is needed. The export contains password hashes and drafts:
write it outside the web root and transfer it only over an authenticated channel.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import quote

TABLES = {
    'articles': 'cms_article', 'site_settings': 'cms_sitesettings',
    'site_pages': 'cms_sitepage', 'page_sections': 'cms_pagesection',
    'services': 'cms_service', 'projects': 'cms_project',
    'project_photos': 'cms_projectphoto', 'content_imports': 'cms_contentimport',
}
JSON_COLUMNS = {'published_payload', 'source'}


def export_database(source):
    source = Path(source).resolve(strict=True)
    connection = sqlite3.connect('file:' + quote(str(source)) + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('The source database did not pass its integrity check.')
        tables = {}
        for target, original in TABLES.items():
            rows = [dict(row) for row in connection.execute(f'SELECT * FROM "{original}" ORDER BY id')]
            for row in rows:
                for key in JSON_COLUMNS & row.keys():
                    if row[key] is not None:
                        row[key] = json.loads(row[key])
            tables[target] = rows
        tables['users'] = []
        for user in connection.execute('SELECT * FROM auth_user ORDER BY id'):
            name = ' '.join(filter(None, (user['first_name'], user['last_name']))).strip() or user['username']
            tables['users'].append({
                'id': user['id'], 'name': name, 'username': user['username'],
                'email': user['email'] or None, 'password': user['password'],
                'is_staff': bool(user['is_staff']), 'is_active': bool(user['is_active']),
                'created_at': user['date_joined'], 'updated_at': user['date_joined'],
            })
        return {'format': 'orion-django-export', 'version': 1, 'tables': tables}
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = export_database(args.database)
    # An existing export must never be silently replaced with a newer snapshot.
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print('Private export written; ' + ', '.join(f'{key}: {len(rows)}' for key, rows in payload['tables'].items()))


if __name__ == '__main__':
    main()
