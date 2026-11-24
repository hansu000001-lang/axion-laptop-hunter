"""Best Buy Products + documented Open Box Buying Options APIs."""
import os
import requests
from ..models import Listing
from ..matching import enrich_and_verify

BASE = 'https://api.bestbuy.com/v1/products'
OPEN_BOX = 'https://api.bestbuy.com/beta/products/openBox'


def fetch():
    key = os.getenv('BESTBUY_API_KEY')
    if not key:
        return []

    params = {
        'apiKey': key,
        'format': 'json',
        'show': 'sku,name,salePrice,regularPrice,url,manufacturer,modelNumber,shortDescription,longDescription,condition,onlineAvailability',
        'pageSize': 100,
        'sort': 'salePrice.asc',
    }
    r = requests.get(f'{BASE}(search=275HX)', params=params, timeout=25)
    r.raise_for_status()
    products = r.json().get('products', [])
    out = []
    skus = []

    for x in products:
        sku = str(x.get('sku') or '')
        if not sku:
            continue
        skus.append(sku)
        specs = ' '.join(str(x.get(k) or '') for k in ('shortDescription', 'longDescription', 'modelNumber'))
        item = Listing(
            source='Best Buy', source_id=sku, title=x.get('name', ''),
            url=x.get('url') or f'https://www.bestbuy.com/site/searchpage.jsp?st={sku}',
            price=float(x['salePrice']) if x.get('salePrice') is not None else None,
            condition=x.get('condition', 'new'),
            availability='in_stock' if x.get('onlineAvailability') else 'unknown',
            specs_text=specs,
        )
        out.append(enrich_and_verify(item))

    # Best Buy's public Buying Options API returns currently available open-box offers.
    # Endpoint accepts up to 100 SKUs per request.
    for start in range(0, len(skus), 100):
        batch = skus[start:start + 100]
        if not batch:
            continue
        query = 'sku in(' + ','.join(batch) + ')'
        ob = requests.get(f'{OPEN_BOX}({query.replace(" ", "%20")})',
                          params={'apiKey': key}, timeout=25,
                          headers={'Accept': 'application/json'})
        ob.raise_for_status()
        for offer_product in ob.json().get('results', []):
            sku = str(offer_product.get('sku') or '')
            title = (offer_product.get('names') or {}).get('title', '')
            specs = (offer_product.get('descriptions') or {}).get('short', '')
            url = (offer_product.get('links') or {}).get('web') or f'https://www.bestbuy.com/site/searchpage.jsp?st={sku}'
            for offer in offer_product.get('offers', []):
                price = (offer.get('prices') or {}).get('current')
                condition = 'open_box_' + str(offer.get('condition') or 'unknown')
                item = Listing(
                    source='Best Buy Open Box', source_id=f'{sku}:{condition}',
                    title=title, url=url, price=float(price) if price is not None else None,
                    condition=condition, availability='in_stock', specs_text=specs,
                )
                out.append(enrich_and_verify(item))
    return out
