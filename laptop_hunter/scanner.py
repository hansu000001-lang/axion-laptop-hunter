import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from .db import connect, save_listing, should_alert, mark_alert, now
from .matching import is_candidate
from .telegram import send
from .sources import ebay, bestbuy, feeds, manual_pages

load_dotenv()
SOURCES=[('eBay',ebay.fetch),('Best Buy',bestbuy.fetch),('Deal/Search Feeds',feeds.fetch),('Configured Public Pages',manual_pages.fetch)]

def scan():
    con=connect(); budget=float(os.getenv('MAX_PRICE_USD','1200')); total=0
    for name,fn in SOURCES:
        started=now()
        try:
            items=fn(); seen=0
            for item in items:
                if not item.url or not item.source_id or not is_candidate(item): continue
                seen+=1; total+=1
                state=save_listing(con,item)
                con.commit()
                # Strict alert: explicit 275HX + at least 32GB RAM + at least 1TB SSD + USD price <= budget + current availability.
                available=item.availability in ('listed','in_stock','available','available_now')
                if state['exact'] and state['under'] and item.currency=='USD' and available and item.price is not None:
                    key=f"deal:{item.price:.2f}:{item.condition}:{item.availability}"
                    if should_alert(con,item.source,item.source_id,key):
                        msg=(f"🚨 AXION LAPTOP DEAL\n\n{item.title}\n\n"
                             f"Price: ${item.price:.2f} USD"+(f" + ${item.shipping:.2f} shipping" if item.shipping else "")+"\n"
                             f"Condition: {item.condition}\nSeller: {item.seller or 'Not provided'}\n"
                             f"CPU: Intel Core Ultra 9 275HX\nRAM: {item.ram_gb}GB\nSSD: {item.ssd_gb}GB\nGPU: {item.gpu or 'Not specified'}\n"
                             f"Source: {item.source}\nLink: {item.url}\n\nObserved: {item.observed_at or now()}\n"
                             "Verify checkout price, shipping, tax and stock before purchase.")
                        if send(msg): mark_alert(con,item.source,item.source_id,key); con.commit()
            print(f'[OK] {name}: {seen} candidates')
        except Exception as e:
            con.execute('INSERT INTO scan_runs(started_at,finished_at,source,status,items_seen,error) VALUES(?,?,?,?,?,?)',(started,now(),name,'error',0,str(e)[:1000])); con.commit()
            print(f'[ERROR] {name}: {e}')
    # Keep only the latest 180 days of price observations. This bounds the tracked DB.
    from datetime import timedelta
    cutoff=(datetime.now(timezone.utc)-timedelta(days=180)).isoformat(timespec='seconds')
    con.execute('DELETE FROM price_history WHERE observed_at < ?', (cutoff,))
    con.execute('DELETE FROM scan_runs WHERE id NOT IN (SELECT id FROM scan_runs ORDER BY id DESC LIMIT 100)')
    con.commit()
    print(f'Scan complete. Candidate listings processed: {total}')
    con.close()

if __name__=='__main__': scan()
