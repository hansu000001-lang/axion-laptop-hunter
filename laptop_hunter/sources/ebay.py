import os, requests
from urllib.parse import quote
from ..models import Listing
from ..matching import enrich_and_verify

TOKEN_URL='https://api.ebay.com/identity/v1/oauth2/token'
API='https://api.ebay.com/buy/browse/v1/item_summary/search'

def _token():
    cid=os.getenv('EBAY_CLIENT_ID'); secret=os.getenv('EBAY_CLIENT_SECRET')
    if not cid or not secret: return None
    r=requests.post(TOKEN_URL,auth=(cid,secret),headers={'Content-Type':'application/x-www-form-urlencoded'},data={'grant_type':'client_credentials','scope':'https://api.ebay.com/oauth/api_scope'},timeout=25)
    r.raise_for_status(); return r.json()['access_token']

def fetch():
    token=_token()
    if not token: return []
    out=[]
    terms=['"275HX" laptop 32GB 1TB','"Ultra 9 275HX" laptop','275HX gaming laptop']
    for term in terms:
        params={'q':term,'limit':50,'sort':'newlyListed','filter':'buyingOptions:{FIXED_PRICE},priceCurrency:USD,price:[..1200]'}
        r=requests.get(API,params=params,headers={'Authorization':f'Bearer {token}','X-EBAY-C-MARKETPLACE-ID':'EBAY_US'},timeout=25)
        if r.status_code==429: break
        r.raise_for_status()
        for x in r.json().get('itemSummaries',[]):
            price=x.get('price') or {}
            cond=x.get('condition','unknown')
            item=Listing(source='eBay',source_id=x.get('itemId',''),title=x.get('title',''),url=x.get('itemWebUrl',''),price=float(price.get('value')) if price.get('value') else None,currency=price.get('currency','USD'),condition=cond,seller=(x.get('seller') or {}).get('username',''),availability='listed',specs_text=x.get('shortDescription','') or '')
            out.append(enrich_and_verify(item))
    return out
