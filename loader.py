"""Loading code from 01_load_clean.ipynb as importable functions, so any domain can be loaded the same way."""
import json
import re
from pathlib import Path

import pandas as pd

LOG_ROOT = Path('nginx-logs')
TEXT_TIME = '%d/%b/%Y:%H:%M:%S %z'
NUMERIC = ['status_code', 'response_time', 'response_body_size', 'request_length']

LINE_RE = re.compile(
    r'(?P<client_address>\S+) (?P<request_id>\S+) (?P<user>\S+) '
    r'\[(?P<datetime>[^\]]+)\] '
    r'"(?P<request>[^"]*)" '
    r'(?P<status_code>\d{3}) (?P<response_body_size>\d+) '
    r'"(?P<http_referrer>[^"]*)" '
    r'"(?P<http_user_agent>[^"]*)" '
    r'(?P<response_time>\S+)'
)


def load_json(path):
    rows = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.endswith(',}'):
                line = line[:-2] + '}'
            rows.append(json.loads(line))

    df = pd.DataFrame(rows)
    df['domain'] = path.parts[1]
    df['subdomain'] = path.parts[2]
    df['source'] = 'json'
    return df


def load_text(path):
    rows, bad = [], []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            m = LINE_RE.fullmatch(line)
            if m:
                rows.append(m.groupdict())
            else:
                bad.append(line)

    if bad:
        print(f'{path.name}: {len(bad)} bad lines')

    df = pd.DataFrame(rows)
    df['domain'] = path.parts[1]
    df['subdomain'] = path.parts[2]
    df['host'] = path.name.split('.access.')[0]
    twin = path.with_name(path.name.replace('.access.', '.access.json.'))
    df['source'] = 'text_gap' if twin.exists() else 'text_only'
    return df


def to_numbers(df):
    for col in NUMERIC:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def load_domain(domain):
    """All requests of one domain: JSON rows plus text rows JSON missed. Empty DataFrame if no logs."""
    folder = LOG_ROOT / domain
    json_files = [p for p in folder.glob('*/*.access.json.*.log') if p.stat().st_size]
    text_files = [p for p in folder.glob('*/*.access.*log')
                  if '.access.json.' not in p.name and p.stat().st_size]

    parts = []
    if json_files:
        df_json = pd.concat([load_json(p) for p in json_files], ignore_index=True)
        df_json['datetime'] = pd.to_datetime(df_json.datetime).dt.tz_convert('Asia/Seoul')
        parts.append(to_numbers(df_json.drop(columns=['user'], errors='ignore')))
    if text_files:
        df_text = pd.concat([load_text(p) for p in text_files], ignore_index=True)
        if json_files:
            df_text = df_text[~df_text.request_id.isin(parts[0].request_id)].copy()
        if len(df_text):
            pieces = df_text['request'].str.split(' ', n=2)
            for i, col in enumerate(['method', 'uri', 'http_version']):
                df_text[col] = pieces.str[i]
            df_text['datetime'] = pd.to_datetime(df_text.datetime, format=TEXT_TIME).dt.tz_convert('Asia/Seoul')
            parts.append(to_numbers(df_text.drop(columns=['user'])))

    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    return df.replace({'': pd.NA, '-': pd.NA})


def domains():
    return sorted(p.name for p in LOG_ROOT.iterdir() if p.is_dir())
