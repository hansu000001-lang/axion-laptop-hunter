import os, sqlite3
from pathlib import Path
from datetime import datetime, timezone

SCHEMA = '''
CREATE TABLE IF NOT EXISTS listings (
 source TEXT NOT NULL, source_id TEXT NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL,
 first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, latest_price REAL, latest_shipping REAL DEFAULT 0,
 currency TEXT DEFAULT 'USD', condition TEXT, seller TEXT, availability TEXT,
 cpu TEXT, ram_gb INTEGER, ssd_gb INTEGER, gpu TEXT, specs_text TEXT,
 exact_match INTEGER DEFAULT 0, under_budget INTEGER DEFAULT 0, confidence TEXT,
 PRIMARY KEY(source, source_id));
CREATE TABLE IF NOT EXISTS price_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, source_id TEXT NOT NULL,
 observed_at TEXT NOT NULL, price REAL, shipping REAL, availability TEXT,
 FOREIGN KEY(source, source_id) REFERENCES listings(source, source_id));
CREATE TABLE IF NOT EXISTS alerts_sent (
 source TEXT NOT NULL, source_id TEXT NOT NULL, alert_key TEXT NOT NULL, sent_at TEXT NOT NULL,
 PRIMARY KEY(source, source_id, alert_key));
CREATE TABLE IF NOT EXISTS scan_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, finished_at TEXT,
 source TEXT, status TEXT, items_seen INTEGER DEFAULT 0, error TEXT);
'''

def connect(path=None):
    path = path or os.getenv('DATABASE_PATH', 'data/laptop_hunter.sqlite3')
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript(SCHEMA)
    return con

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')

def save_listing(con, x):
    """Persist only first sightings or meaningful changes (not every polling pass)."""
    d=x.to_dict(); stamp=d.get('observed_at') or now()
    existing=con.execute('''SELECT * FROM listings WHERE source=? AND source_id=?''', (d['source'],d['source_id'])).fetchone()
    first=existing['first_seen'] if existing else stamp
    exact = int(d.get('confidence') == 'verified' and d.get('cpu') and d.get('ram_gb')==32 and d.get('ssd_gb')==1024)
    under = int(bool(d.get('price') is not None and d.get('price') + (d.get('shipping') or 0) <= float(os.getenv('MAX_PRICE_USD','1200'))))
    values=(d['title'],d['url'],d.get('price'),d.get('shipping',0),d.get('currency','USD'),d.get('condition'),d.get('seller'),d.get('availability'),d.get('cpu'),d.get('ram_gb'),d.get('ssd_gb'),d.get('gpu'),d.get('specs_text'),exact,under,d.get('confidence','unverified'))
    if existing is None:
        con.execute('''INSERT INTO listings(source,source_id,title,url,first_seen,last_seen,latest_price,latest_shipping,currency,condition,seller,availability,cpu,ram_gb,ssd_gb,gpu,specs_text,exact_match,under_budget,confidence)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (d['source'],d['source_id'],d['title'],d['url'],first,stamp,*values[2:]))
        con.execute('INSERT INTO price_history(source,source_id,observed_at,price,shipping,availability) VALUES(?,?,?,?,?,?)', (d['source'],d['source_id'],stamp,d.get('price'),d.get('shipping',0),d.get('availability')))
        changed=True
    else:
        old=(existing['title'],existing['url'],existing['latest_price'],existing['latest_shipping'],existing['currency'],existing['condition'],existing['seller'],existing['availability'],existing['cpu'],existing['ram_gb'],existing['ssd_gb'],existing['gpu'],existing['specs_text'],existing['exact_match'],existing['under_budget'],existing['confidence'])
        changed = old != values
        if changed:
            con.execute('''UPDATE listings SET title=?,url=?,last_seen=?,latest_price=?,latest_shipping=?,currency=?,condition=?,seller=?,availability=?,cpu=?,ram_gb=?,ssd_gb=?,gpu=?,specs_text=?,exact_match=?,under_budget=?,confidence=? WHERE source=? AND source_id=?''', (d['title'],d['url'],stamp,d.get('price'),d.get('shipping',0),d.get('currency','USD'),d.get('condition'),d.get('seller'),d.get('availability'),d.get('cpu'),d.get('ram_gb'),d.get('ssd_gb'),d.get('gpu'),d.get('specs_text'),exact,under,d.get('confidence','unverified'),d['source'],d['source_id']))
            price_changed = (existing['latest_price'] != d.get('price') or existing['latest_shipping'] != (d.get('shipping') or 0) or existing['availability'] != d.get('availability'))
            if price_changed:
                con.execute('INSERT INTO price_history(source,source_id,observed_at,price,shipping,availability) VALUES(?,?,?,?,?,?)', (d['source'],d['source_id'],stamp,d.get('price'),d.get('shipping',0),d.get('availability')))
    return {'is_new': existing is None, 'changed': changed, 'exact': bool(exact), 'under': bool(under), 'first_seen': first}

def should_alert(con, source, source_id, key):
    return con.execute('SELECT 1 FROM alerts_sent WHERE source=? AND source_id=? AND alert_key=?',(source,source_id,key)).fetchone() is None

def mark_alert(con, source, source_id, key):
    con.execute('INSERT OR IGNORE INTO alerts_sent VALUES(?,?,?,?)',(source,source_id,key,now()))
