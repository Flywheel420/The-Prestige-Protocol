import urllib.request
import zipfile
import io
import csv
import time
from pathlib import Path

# ================== CONFIG ==================
PERIODS = [
    'cnsfails202508a', 'cnsfails202508b',
    'cnsfails202509a', 'cnsfails202509b',
    'cnsfails202510a', 'cnsfails202510b',
    'cnsfails202511a', 'cnsfails202511b',
    'cnsfails202512a', 'cnsfails202512b',
    'cnsfails202601a', 'cnsfails202601b',
    'cnsfails202602a', 'cnsfails202602b',
]

TARGETS = {
    '36467W109': 'GME',
    '36467W117': 'GME.WS',
}

BASE_URL = 'https://www.sec.gov/files/data/fails-deliver-data/'
HEADERS = {'User-Agent': 'GME FTD Research research@example.com'}
OUTPUT_FILE = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'gme_ftd_aug2025_feb2026.csv'
# ===========================================

rows = []
failed_periods = []

for i, period in enumerate(PERIODS, 1):
    url = f'{BASE_URL}{period}.zip'
    print(f'[{i:2d}/{len(PERIODS)}] Fetching {period}...', end=' ', flush=True)

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            zip_bytes = resp.read()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    content = f.read().decode('utf-8', errors='replace')
                    for line in content.split('\n')[1:]:
                        parts = line.strip().split('|')
                        if len(parts) < 5:
                            continue
                        settlement_date, cusip, symbol, quantity, description = parts[:5]
                        price = parts[5] if len(parts) > 5 else ''
                        if cusip.strip() in TARGETS:
                            rows.append({
                                'settlement_date': settlement_date.strip(),
                                'label': TARGETS[cusip.strip()],
                                'cusip': cusip.strip(),
                                'symbol': symbol.strip(),
                                'quantity': int(quantity.strip()) if quantity.strip().isdigit() else 0,
                                'price': price.strip(),
                                'description': description.strip(),
                            })
        print('OK')
        time.sleep(0.3)  # be nice to SEC servers

    except Exception as e:
        print(f'FAIL ({e})')
        failed_periods.append(period)

# Save results
if rows:
    rows.sort(key=lambda r: (r['settlement_date'], r['label']))
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['settlement_date', 'label', 'cusip', 'symbol', 'quantity', 'price', 'description'])
        writer.writeheader()
        writer.writerows(rows)
    print(f'\nWrote {len(rows)} rows -> {OUTPUT_FILE.resolve()}')
else:
    print('\nNo matching rows found.')

# Summary
gme = [r for r in rows if r['label'] == 'GME']
gme_ws = [r for r in rows if r['label'] == 'GME.WS']
print(f'GME rows: {len(gme)} | GME.WS rows: {len(gme_ws)}')

if gme:
    peak = max(gme, key=lambda r: r['quantity'])
    print(f'GME peak: {peak["settlement_date"]} -> {peak["quantity"]:,} fails')

if gme_ws:
    peak_ws = max(gme_ws, key=lambda r: r['quantity'])
    print(f'GME.WS peak: {peak_ws["settlement_date"]} -> {peak_ws["quantity"]:,} fails')

if failed_periods:
    print(f'\nFailed periods: {failed_periods}')
