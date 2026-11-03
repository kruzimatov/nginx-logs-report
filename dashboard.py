"""Nginx log dashboard. Run: streamlit run dashboard.py"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path('data/logs_all.parquet')
if not DATA.exists():
    DATA = Path('data/logs.parquet')  # ponytail: falls back to 01_load_clean.ipynb output until 04_all_domains_and_dashboard.ipynb has run

st.set_page_config(page_title='Nginx Log Dashboard', layout='wide')


@st.cache_data
def load(path):
    df = pd.read_parquet(path, columns=[
        'datetime', 'domain', 'subdomain', 'status_code', 'response_time',
        'client_address', 'uri', 'country', 'source'])
    df['status_class'] = (df.status_code // 100).astype(str) + 'xx'
    df['path'] = df.uri.str.split('?').str[0]  # query strings can carry tokens: never shown
    return df.drop(columns=['uri'])


df = load(DATA)

with st.sidebar:
    st.header('Filters')
    domains = st.multiselect('Domain', sorted(df.domain.unique()))
    scope = df[df.domain.isin(domains)] if domains else df
    subdomains = st.multiselect('Subdomain', sorted(scope.subdomain.unique()))
    first, last = df.datetime.min().date(), df.datetime.max().date()
    dates = st.date_input('Dates', (first, last), min_value=first, max_value=last)
    classes = st.multiselect('Status', sorted(df.status_class.unique()), default=sorted(df.status_class.unique()))
    hide_honeypot = st.checkbox('Hide honeypot', value=True)

view = scope[scope.subdomain.isin(subdomains)] if subdomains else scope
if hide_honeypot:
    view = view[view.subdomain != 'a-honeypot']
if len(dates) == 2:
    day = view.datetime.dt.date
    view = view[(day >= dates[0]) & (day <= dates[1])]
view = view[view.status_class.isin(classes)]

st.title('Nginx Log Dashboard')
st.caption(f'{DATA} · {len(view):,} of {len(df):,} requests match the filters')

if view.empty:
    st.info('No requests match these filters.')
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric('Requests', f'{len(view):,}')
c2.metric('Server errors (5xx)', f'{(view.status_code >= 500).mean():.1%}')
c3.metric('Median response', f'{view.response_time.median():.3f} s')
c4.metric('Unique IPs', f'{view.client_address.nunique():,}')

hourly = view.groupby([pd.Grouper(key='datetime', freq='1h'), 'status_class']).size().reset_index(name='requests')
st.plotly_chart(px.area(hourly, x='datetime', y='requests', color='status_class', title='Requests per hour'),
                width='stretch')

left, right = st.columns(2)
by_sub = (view.groupby('subdomain')
              .agg(requests=('status_code', 'size'), error_share=('status_code', lambda s: (s >= 500).mean()))
              .sort_values('requests', ascending=False).head(15).reset_index())
left.plotly_chart(px.bar(by_sub, x='requests', y='subdomain', orientation='h', color='error_share',
                         title='Top subdomains (colour = 5xx share)'), width='stretch')
countries = view[~view.country.isin(['internal', 'unknown'])].country.value_counts().head(10).reset_index()
right.plotly_chart(px.bar(countries, x='country', y='count', title='Top countries'), width='stretch')

st.subheader('Slowest paths (at least 20 requests, WebSocket excluded)')
slow = (view[view.status_code != 101]
            .groupby(['subdomain', 'path']).response_time.agg(['count', 'median', 'max'])
            .query('count >= 20').sort_values('median', ascending=False).head(20).round(3))
st.dataframe(slow, width='stretch')
