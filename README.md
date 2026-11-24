# AXION Laptop Hunter — Zero-cost GitHub edition

Automated US laptop listing monitor with Telegram alerts, SQLite price history and a local Streamlit dashboard.

## Exact matching rules

A purchase alert requires all of the following:

- Intel **Core Ultra 9 275HX** (not merely a listing containing `275HX` without the Ultra 9 model context)
- **32GB installed RAM**
- **1TB SSD (1024GB reported capacity)**
- **Any GPU** — GPU model is recorded for display only and never used as a filter
- Item price plus known shipping at or below **USD $1,200**
- USD pricing and a source availability signal
- New, open-box, refurbished or used condition; condition is reported in the alert

The matcher is conservative: if the source does not explicitly expose enough specification text to verify CPU, RAM and SSD, the listing is stored as an unverified candidate and does not generate an exact-match alert.

## Zero-cost operating model

The free configuration uses:

1. **GitHub Actions** on a **public repository** with standard `ubuntu-latest` runners. GitHub documents standard runner usage as free and unlimited for public repositories. Source code and tracked deal history are public; repository secrets are not published.
2. **Telegram Bot API** for free push notifications.
3. **SQLite stored in the Git repository**, not as a GitHub Actions artifact. Artifacts/logs have retention periods; committed repository files do not automatically expire. The scanner commits the database only when a listing or price/availability actually changes, not every five-minute polling pass.
4. **Free official APIs and RSS**: eBay Browse API, Best Buy Products/Buying Options APIs, and Google News RSS discovery.
5. **No Keepa, paid proxy, paid scraping service, VPS, or paid database** in the zero-cost edition.

GitHub public-repository standard runners are free, while private repositories have monthly included minutes and can incur charges if exceeded. See https://docs.github.com/en/billing/concepts/product-billing/github-actions and https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax.

## Sources and coverage limits

- **eBay Browse API**: searches fixed-price US listings, newest first; listings can be new, open-box, refurbished or used depending on seller condition. Requires free eBay developer application credentials and remains subject to API access/rate limits.
- **Best Buy Products API**: catalog search and product specs/prices.
- **Best Buy Buying Options API**: documented open-box offers, condition and price for product SKUs returned by catalog search. Best Buy says its open-box data includes currently available products and checks for newly available items every five minutes. API access requires a Best Buy developer key.
- **Google News RSS**: free indexed deal/article discovery across retailer domains. It is a discovery source, not a live inventory or price guarantee.
- **Configured public product pages**: only URLs the user explicitly supplies and which permit automated access. No login, CAPTCHA solving, proxy rotation, anti-bot evasion or access-control bypass.

This is broad discovery, not literally every listing on every US platform. Walmart, Newegg, Costco, Amazon, manufacturer stores and Facebook Marketplace do not all provide a generally available free search API. Google News may surface indexed deal pages, but it cannot guarantee fresh prices or inventory. Facebook Marketplace is not scraped. For truly complete coverage or richer Amazon offer data, a paid/partner feed may be necessary; this project does not silently subscribe to one.

Official docs:
- eBay Browse API: https://developer.ebay.com/develop/api/buy/browse_api
- Best Buy APIs: https://developer.bestbuy.com/apis
- Best Buy API docs, including Buying Options/Open Box: https://bestbuyapis.github.io/api-documentation/
- GitHub Actions billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions

## Persistence: does GitHub storage expire?

- **Actions artifacts and logs** expire according to retention settings (default 90 days). This project does not use artifacts for its database.
- **The SQLite database is committed to `data/laptop_hunter.sqlite3` in the repository**, so it remains in Git history until the repository/history is deleted. It is not an artifact.
- To avoid bloat, the database records price history only for new listings or meaningful price/shipping/availability changes and prunes live price-history rows older than 180 days. Old Git commits remain in repository history, but the candidate set is small and only meaningful changes create commits.
- GitHub recommends keeping repositories ideally below 1GB and strongly recommends below 5GB. Check repository size occasionally; this should remain small for this narrow CPU filter.

## Setup

### 1. Create a Telegram bot (free)

1. In Telegram, open `@BotFather`, send `/newbot`, and follow the steps.
2. Copy the bot token.
3. Open your new bot and send it `/start` or a message.
4. In a browser, open `https://api.telegram.org/botYOUR_TOKEN/getUpdates`.
5. Copy `message.chat.id` from the returned JSON.

### 2. Create free API credentials

**eBay:** create an application at https://developer.ebay.com/ and copy the Production Client ID and Client Secret. Browse API requires an application access token. Developer access and rate limits are controlled by eBay.

**Best Buy:** request an API key at https://developer.bestbuy.com/. The Products API returns catalog, price and specification information; Buying Options API documents open-box offers. Best Buy controls key access and quotas.

No Keepa key is used or needed.

### 3. Create a public GitHub repository

A public repository is the way to use GitHub-hosted standard runners without consuming private-repository monthly minutes. The code and deal-history database will be public, but properly configured GitHub Actions secrets are not exposed in the repository. Do not put credentials in source files, commits, issue text or logs.

1. Create a repository, e.g. `axion-laptop-hunter`, and set visibility to **Public**.
2. Upload/push all project files, including the `.github/workflows` folder.
3. Open **Settings → Secrets and variables → Actions → New repository secret**.
4. Add these secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `EBAY_CLIENT_ID`
   - `EBAY_CLIENT_SECRET`
   - `BESTBUY_API_KEY`
5. Open **Settings → Actions → General → Workflow permissions** and allow read/write access to repository contents.
6. Open **Actions** and enable workflows if prompted.
7. Run **AXION Laptop Hunter scan → Run workflow** once to test.

### 4. Git push commands (if uploading from your PC)

```bash
git init
git add .
git commit -m "Initial AXION Laptop Hunter"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/axion-laptop-hunter.git
git push -u origin main
```

### 5. No dashboard babysitting required

Telegram is the primary interface. Once the workflow is enabled and secrets are correct, the scanner runs automatically and sends a message only when it finds a verified match under the budget. A workflow failure also sends a Telegram warning when Telegram secrets are configured. A separate monthly heartbeat sends one Telegram confirmation and creates a small commit to keep the public-repository schedule active.

The Streamlit dashboard is optional and can be run locally:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
streamlit run app.py
```

No dashboard hosting is required for alerts. GitHub Pages or Streamlit Community Cloud can be added later, but neither is needed for the unattended scanner.

## Schedule and unattended operation

- The scan workflow targets every five minutes (`2/5 * * * *`). GitHub says five minutes is the shortest scheduled interval.
- GitHub can delay or drop scheduled runs during high load. This is not a guaranteed real-time service.
- GitHub automatically disables scheduled workflows in public repositories after 60 days without repository activity. The included monthly keepalive workflow creates a small monthly commit to maintain activity. If GitHub ever disables it, re-enable it under **Actions**.
- A separate concurrency group prevents two runs from updating SQLite simultaneously.

## Local commands

```bash
python -m laptop_hunter.scanner
streamlit run app.py
```

## Operational notes

- Tax is not included because it depends on the US delivery address.
- Shipping is included only when a source provides it; verify final checkout total.
- API/feed search results can be incomplete or stale. Open the product URL and verify stock, seller, condition and checkout price before purchase.
- This software only discovers and alerts. It does not buy products or log into retailer accounts.
