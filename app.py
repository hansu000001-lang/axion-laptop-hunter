import os, sqlite3
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
load_dotenv()
DB=os.getenv('DATABASE_PATH','data/laptop_hunter.sqlite3')
st.set_page_config(page_title='AXION Laptop Hunter',page_icon='💻',layout='wide')
st.title('💻 AXION Laptop Hunter')
st.caption('Intel Core Ultra 9 275HX · 32GB RAM · 1TB SSD · Any GPU · Maximum $1,200')
if not os.path.exists(DB):
    st.info('No scan database yet. Run the GitHub Actions workflow or `python -m laptop_hunter.scanner`.')
    st.stop()
con=sqlite3.connect(DB)
try:
    df=pd.read_sql_query('SELECT * FROM listings ORDER BY last_seen DESC',con)
    hist=pd.read_sql_query('SELECT * FROM price_history ORDER BY observed_at DESC',con)
    runs=pd.read_sql_query('SELECT * FROM scan_runs ORDER BY id DESC LIMIT 50',con)
except Exception as e:
    st.error(f'Database could not be read: {e}'); st.stop()
finally: con.close()
if df.empty:
    st.warning('No candidate listings collected yet.')
else:
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Candidates',len(df)); c2.metric('Verified exact matches',int(df.exact_match.sum())); c3.metric('Under $1,200',int(df.under_budget.sum())); c4.metric('Sources seen',df.source.nunique())
    tabs=st.tabs(['Potential deals','All candidates','Price history','Scanner health'])
    with tabs[0]:
        deals=df[(df.exact_match==1)&(df.under_budget==1)].copy()
        st.caption('Only verified specification matches are shown here. Availability still needs checkout confirmation unless the source explicitly reports stock.')
        if deals.empty: st.info('No verified exact-spec listings under budget have been recorded yet.')
        else:
            for _,r in deals.iterrows():
                with st.container(border=True):
                    st.subheader(r.title)
                    st.write(f"${r.latest_price:,.2f} · {r.condition} · {r.source} · {r.availability}")
                    st.write(f"CPU: {r.cpu} | RAM: {r.ram_gb}GB | SSD: {r.ssd_gb}GB | GPU: {r.gpu or 'Unknown'}")
                    st.link_button('Open listing',r.url)
    with tabs[1]:
        q=st.text_input('Filter listings')
        view=df.copy()
        if q: view=view[view.astype(str).apply(lambda col: col.str.contains(q,case=False,na=False)).any(axis=1)]
        st.dataframe(view,hide_index=True,use_container_width=True,column_config={'url':st.column_config.LinkColumn('Product link')})
        st.download_button('Download CSV',view.to_csv(index=False).encode(),file_name='axion_laptop_candidates.csv',mime='text/csv')
    with tabs[2]:
        if not hist.empty:
            ids=df[['source','source_id','title']].drop_duplicates()
            opts={f"{x.title[:90]} [{x.source}]":(x.source,x.source_id) for x in ids.itertuples()}
            selected=st.selectbox('Product',list(opts))
            src,sid=opts[selected]
            h=hist[(hist.source==src)&(hist.source_id==sid)].copy()
            if not h.empty:
                h['observed_at']=pd.to_datetime(h.observed_at,errors='coerce')
                st.line_chart(h.set_index('observed_at')[['price']].sort_index())
                st.dataframe(h.sort_values('observed_at',ascending=False),hide_index=True,use_container_width=True)
            else: st.info('No price history recorded.')
    with tabs[3]:
        st.dataframe(runs,hide_index=True,use_container_width=True)
st.caption('Data can be delayed, incomplete or stale. A listing is not a confirmed purchase offer until verified at retailer checkout.')
