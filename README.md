# Nginx Logs Report

Analysis of one week of nginx access and error logs for humblebee.ai and hbai.dev
(1,187,827 requests, 2026-10-21 to 2026-10-29, Asia/Seoul time).

## Notebooks

| Notebook | What it does |
|---|---|
| `analysis.ipynb` | Day 1: loads JSON and text access logs, fixes and merges them, saves `data/logs.parquet` |
| `02_traffic_and_clients.ipynb` | Day 2: status codes, traffic over time, slow endpoints, client types, IP kinds, location |
| `03_errors_and_causes.ipynb` | Day 3: 5xx per service, error bursts, nginx error logs, reloads, scanners, likely causes |
| `04_all_domains_and_dashboard.ipynb` | Day 4: summary of all findings, loader run on every domain, saves `data/logs_all.parquet` |

`loader.py` holds the Day 1 loading code as reusable functions. `dashboard.py` is a Streamlit dashboard over the Parquet data. `PLAN.md` is the task checklist.

## Key findings

- The JSON access log misses static files: 32,299 requests (99.3% static) exist only in the text log. Likely a `location` block with its own `access_log`.
- The `$remote_user` field contained API keys and an email. The column was dropped.
- Machines send most traffic: monitoring 35.3%, browsers 31.0%, scripts 21.8%, AI agents 7.7%.
- speakology, smart-office and repo-holmes were down the whole week (mostly 502).
- On 2026-10-28 up to 12 services failed in the same 10 minutes: a shared failure, not one app.
- hstaff `/mcp` errors all go to one upstream: refused connections and read timeouts.
- nginx reloads do not cause errors. 200 responses on secret paths are catch-all pages, no evidence of a leak.

## Data and privacy

The raw logs (`nginx-logs/`) and the generated Parquet files (`data/`) are **not** in this repository.
They contain real visitor IPs, locations and request URLs. Public IPs shown in notebook outputs are masked (`20.194.17.x`).

## How to run

```
python -m venv .venv
source .venv/bin/activate
pip install pandas pyarrow plotly jupyter streamlit
```

1. Put the logs in `nginx-logs/<domain>/<subdomain>/`.
2. Run `analysis.ipynb`. It creates `data/logs.parquet`.
3. Run `02_traffic_and_clients.ipynb`, then `03_errors_and_causes.ipynb`.
4. Run `04_all_domains_and_dashboard.ipynb`. It creates `data/logs_all.parquet`.
5. Start the dashboard: `streamlit run dashboard.py`. It runs locally and is not deployed, because it needs the private data.
