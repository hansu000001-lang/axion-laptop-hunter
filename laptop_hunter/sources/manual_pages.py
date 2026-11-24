"""Optional user-specified public product/search URLs. Fetches only explicitly configured URLs.
No login, CAPTCHA solving, proxy rotation, bot evasion, or access-control bypass.
"""
import os, requests
from bs4 import BeautifulSoup
from ..models import Listing
from ..matching import enrich_and_verify

def fetch():
    urls=[u.strip() for u in os.getenv('PUBLIC_PAGE_URLS','').split(',') if u.strip()]
    out=[]
    for i,url in enumerate(urls):
        r=requests.get(url,headers={'User-Agent':'AXION-Laptop-Hunter/1.0 (personal price monitor)'},timeout=20)
        if r.status_code in (401,403,429): continue
        r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        title=(soup.title.get_text(' ',strip=True) if soup.title else url)
        text=soup.get_text(' ',strip=True)[:12000]
        # JSON-LD product price is used only if directly present.
        price=None
        for node in soup.select('script[type="application/ld+json"]'):
            raw=node.string or node.get_text()
            if '"price"' in raw:
                import json,re
                try:
                    data=json.loads(raw); stack=data if isinstance(data,list) else [data]
                    while stack:
                        obj=stack.pop()
                        if isinstance(obj,dict):
                            offers=obj.get('offers')
                            if isinstance(offers,dict) and offers.get('price'):
                                price=float(offers['price']); break
                            if isinstance(offers,list): stack.extend(offers)
                            stack.extend(v for v in obj.values() if isinstance(v,(dict,list)))
                        elif isinstance(obj,list): stack.extend(obj)
                except Exception: pass
        item=Listing(source='Configured Public Page',source_id=str(i)+':'+url,title=title,url=url,price=price,condition='unknown',availability='unknown',specs_text=text)
        out.append(enrich_and_verify(item))
    return out
