# Log Analysis Plan (4 days)

Scope: `nginx-logs/humblebee.ai` and `nginx-logs/hbai.dev` first. Other domains reuse the same loader.
Deliverables: Jupyter notebook (pandas + plotly) and a Streamlit dashboard.
Rule: I write the code.

## Day 1: Load and clean

### What the files look like
Every subdomain folder has up to 3 kinds of file:
- `X.access.json.2026-10-28.log`: one JSON object per line. Has `country`, `city`, `proxy_ip`. Best source.
- `X.access.2026-10-28.log`: same requests as plain text. No country/city.
- `X.access.log` (no date): text only, no JSON twin. Only `hstaff`, `api-hstaff`, `rise`. hstaff + api-hstaff = 120k lines, and they are the only ones with error logs. You cannot skip them.

Text line format (fields in order):
`IP request_id - [time] "METHOD URI PROTOCOL" status size "referrer" "user_agent" response_time`

Both formats carry `request_id`. That is your join key between them.

### Strategy
1. JSON files are the main source.
2. Text files that have no JSON twin: parse with regex into the same column names.
3. `pd.concat` both into one DataFrame. Add a `source` column (`json` / `text`) so you can always tell them apart.

### Steps and hints
- [x] **1. One JSON file.** `pd.read_json(path, lines=True)` fails. Open the file and look at the last characters of a line. Fix each line with a string method, then `json.loads`. Result: list of dicts, then `pd.DataFrame`.
- [x] **2. Wrap it in a function** `load_json(path) -> DataFrame`. You will call it hundreds of times.
- [x] **3. Find all JSON files.** `Path('nginx-logs/humblebee.ai').rglob('*.access.json.*.log')`. Count them: expect 284 for humblebee.ai, 99 for hbai.dev.
- [x] **4. Load all JSON.** List of DataFrames, then one `pd.concat(..., ignore_index=True)`. Never concat inside the loop (slow).
- [x] **5. Add columns from the path.** `domain` = folder under `nginx-logs`, `subdomain` = the folder below it. Hint: `path.parts`.
- [x] **6. Find text-only files.** For each text file, build the JSON twin name (replace `.access.` with `.access.json.`) and check `.exists()`. Print the ones without a twin.
- [x] **7. Regex for one text line.** Test on a single line first. Use named groups `(?P<status_code>\d{3})` so the names match the JSON columns. Hint: the quoted parts are `"([^"]*)"`.
- [x] **8. Function `load_text(path)`.** Lines that do not match the regex: count them, print a few. Do not silently drop them.
- [x] **9. Concat JSON + text-only** into `df`, with the `source` column.
- [x] **10. Types.** `pd.to_datetime(df.datetime)` for JSON. Text time is `21/Oct/2026:14:38:43 +0900`, needs `format=`. `pd.to_numeric(..., errors='coerce')` for `status_code`, `response_time`, `response_body_size`.
- [x] **11. Check quality.** `df.isna().sum()`, `df.duplicated('request_id').sum()`, `df.dtypes`.
- [x] **12. Save.** `df.to_parquet('data/logs.parquet')`. Reload it and confirm the row count is the same.

### Investigation (good finding for the report)
Some days the JSON file has fewer lines than its text twin (example: `attendance` 2026-10-21, 1432 JSON vs 1694 text). Same first request, different ending.
- Load both, compare `request_id` sets. Which requests are missing from JSON?
- Look at them: is it a time range (JSON logging started or stopped), or a kind of request (websocket, errors)?
- Decide: if JSON is missing data, you may need the text version for those days too. Write down your decision.

## Day 2: Mining
- [x] Status breakdown (2xx/3xx/4xx/5xx) per subdomain.
- [x] Traffic per day and per hour (`resample('1h')`).
- [x] Slowest endpoints by `response_time`. Separate long-lived connections (websocket, SSE) from real slowness.
- [x] Top IPs and top user agents. Label bots: monitoring (Uptime-Kuma), scanners, crawlers, real browsers.
- [x] Decide how to treat `a-honeypot.humblebee.ai` (separate it from real traffic).
- [x] Location: JSON already has `country`/`city`. Use a geo API only for missing IPs. Unique IPs only, batched, cached to a file. (Filled from own data; 28,039 rows / 4,213 IPs still unknown, optional MaxMind GeoLite2.)
- [x] Use the real client IP (`client_address`), not Cloudflare (`proxy_ip`).

## Day 3: Errors and causes
- [ ] 5xx timeline per subdomain. Which services are fully down vs failing sometimes?
- [ ] Parse the 2 error logs (hstaff, api-hstaff). Group by error type: refused, timed out, premature close, forbidden.
- [ ] Correlate: errors by hour, after `nginx_reload.log` events, by upstream address.
- [ ] Scanners: many 404/444 from one IP on paths like `/.env`, `/.git`, `/wp-admin`, `/@fs/`.
- [ ] A 200 on `/.env` is not proof of a leak. Compare its response size with the homepage size.
- [ ] Write down a likely cause for each main error group.

## Day 4: Dashboard and generalize
- [ ] Learn Streamlit basics (rerun model, `@st.cache_data`), about 1 to 2 hours.
- [ ] Dashboard reads the Parquet: filters for domain, subdomain, date range, status. Metrics + plotly charts.
- [ ] Run the loader on the other domains to prove it works unchanged.
- [ ] Final pass on the notebook: clear story, findings at the top.

## Privacy
- Logs contain real user IPs and may contain tokens in URLs. Mask tokens before showing anything.
- Never upload raw logs anywhere.
- A geo API sees every IP you send it. Send unique IPs only, or use offline MaxMind GeoLite2.

## Notes
- Timezone in logs is +0900 (KST).
- `nginx-logs-old-bak` (3.7 GB, older) is optional, for a before/after comparison.
