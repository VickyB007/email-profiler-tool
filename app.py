import streamlit as st
import pandas as pd
from duckduckgo_search import DDGS
import requests
import time
import random
from io import BytesIO
from urllib.parse import urlparse
import plotly.express as px

SEARX_INSTANCES = [
    "https://searx.be", 
    "https://priv.au", 
    "https://searxng.site",
    "https://search.ononoki.org"
]

def get_source_category(url, email_domain):
    if not url or url == "N/A": return "None"
    parsed_url = urlparse(url).netloc.lower()
    if any(s in parsed_url for s in ['linkedin.com', 'facebook.com', 'x.com', 'instagram.com']):
        return "Social/Professional Network"
    if any(s in parsed_url for s in ['zoominfo.com', 'apollo.io', 'rocketreach.co', 'lusha.com', 'hunter.io']):
        return "Data Directory"
    if email_domain and email_domain in parsed_url:
        return "Official Company Site"
    return "General Web/Blog"

def search_email(email, ddgs_client):
    query = f'"{email}"'
    email_domain = email.split('@')[-1] if '@' in email else ""
    instance = random.choice(SEARX_INSTANCES)
    try:
        response = requests.get(f"{instance}/search", params={"q": query, "format": "json"}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                top_res = data['results'][0]
                return {"Status": "Found", "Engine": "SearXNG", "Source": top_res.get('url'), "Category": get_source_category(top_res.get('url'), email_domain)}
    except:
        pass
    try:
        results = list(ddgs_client.text(query, max_results=5))
        if results:
            link = results[0].get('href')
            return {"Status": "Found", "Engine": "DuckDuckGo", "Source": link, "Category": get_source_category(link, email_domain)}
    except:
        return {"Status": "Blocked/Error", "Engine": "None", "Source": "N/A", "Category": "Error"}
    return {"Status": "Not Found", "Engine": "None", "Source": "N/A", "Category": "None"}

st.set_page_config(page_title="Email Intelligence Tool", layout="wide")
st.title("🔍 Multi-Engine Email Profiler")

uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
pasted_emails = st.text_area("Or Paste emails (one per line)")

input_df = pd.DataFrame()
if uploaded_file:
    input_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
elif pasted_emails:
    emails = [e.strip() for e in pasted_emails.split('\n') if e.strip()]
    input_df = pd.DataFrame(emails, columns=["Email"])

if not input_df.empty:
    email_col = st.selectbox("Select the column containing Emails", input_df.columns)
    if st.button("🚀 Start Scalable Analysis"):
        total = len(input_df)
        base_delay = 1.2 if total < 20 else 3.5 if total < 100 else 6.0
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        with DDGS() as ddgs:
            for i, email in enumerate(input_df[email_col]):
                email = str(email).strip()
                status_text.text(f"Checking {i+1}/{total}: {email}")
                res_data = search_email(email, ddgs)
                res_data["Email"] = email
                results.append(res_data)
                progress_bar.progress((i + 1) / total)
                time.sleep(base_delay + random.uniform(0.1, 0.9))
        output_df = pd.DataFrame(results)
        st.success("Search Complete!")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(output_df, names='Status', title='Overall Match Rate', hole=.4))
        with c2:
            st.plotly_chart(px.bar(output_df[output_df['Category'] != "None"], x='Category', title='Source Breakdown'))
        st.dataframe(output_df, use_container_width=True)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            output_df.to_excel(writer, index=False)
        st.download_button("📥 Download Final Excel Report", data=buf.getvalue(), file_name="email_results.xlsx")
