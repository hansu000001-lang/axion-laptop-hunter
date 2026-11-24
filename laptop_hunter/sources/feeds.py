import os, urllib.parse, feedparser, requests
from bs4 import BeautifulSoup
from ..models import Listing
from ..matching import enrich_and_verify

TERMS=['"275HX" laptop 32GB 1TB','"Core Ultra 9 275HX" laptop','"275HX" laptop open box','"275HX" laptop refurbished']
DOMAINS=['bestbuy.com','walmart.com','newegg.com','amazon.com','ebay.com','lenovo.com','dell.com','hp.com','asus.com','acer.com','msi.com','costco.com','bhphotovideo.com','microcenter.com','adorama.com','woot.com','backmarket.com','slickdeals.net','dealnews.com']
def fetch():
    feeds=[]
    for term in TERMS:
        q=term+' ('+' OR '.join('site:'+d for d in DOMAINS)+')'
        feeds.append('https://news.google.com/rss/search?q='+urllib.parse.quote(q)+'&hl=en-US&gl=US&ceid=US:en')
    feeds += [x.strip() for x in os.getenv('EXTRA_FEEDS','').split(',') if x.strip()]
    out=[]
    for url in feeds:
        try:
            parsed=feedparser.parse(url)
            for e in parsed.entries[:50]:
                title=BeautifulSoup(e.get('title',''),'html.parser').get_text(' ',strip=True)
                link=e.get('link','')
                summary=BeautifulSoup(e.get('summary',''),'html.parser').get_text(' ',strip=True)
                item=Listing(source='Deal/Search Feed',source_id=e.get('id') or link,title=title,url=link,price=None,condition='unknown',availability='unknown',specs_text=summary)
                out.append(enrich_and_verify(item))
        except Exception:
            continue
    return out
