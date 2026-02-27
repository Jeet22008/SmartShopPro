import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from postgrest import SyncPostgrestClient
from sklearn.linear_model import LinearRegression
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="SmartShop Pro AI Executive", layout="wide", page_icon="📈")

# 2. SECURE CLOUD CONNECTION
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    client = SyncPostgrestClient(f"{url}/rest/v1", headers={"apikey": key, "Authorization": f"Bearer {key}"})
except KeyError:
    st.error("Missing Secrets! Please add SUPABASE_URL and SUPABASE_KEY to your Streamlit Cloud settings.")
    st.stop()

# 3. AUTHENTICATION SYSTEM
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Enterprise Business Login")
    tab_log, tab_sign = st.tabs(["Login", "Create Account"])
    
    with tab_log:
        u = st.text_input("Username", key="l_user")
        p = st.text_input("Password", type="password", key="l_pass")
        if st.button("Access Dashboard"):
            res = client.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid Credentials")
    
    with tab_sign:
        nu = st.text_input("New Username")
        npw = st.text_input("New Password", type="password")
        if st.button("Register Account"):
            client.table("users").insert({"username": nu, "password": npw}).execute()
            st.success("Account created! You can now log in.")
    st.stop()

# --- SIDEBAR: CONTROLS & INPUTS ---
st.sidebar.title(f"👤 {st.session_state.user}")
st.sidebar.header("📝 New Transaction")
s_date = st.sidebar.date_input("Date")
s_prod = st.sidebar.selectbox("Category", ["Electronics", "Grocery", "Apparel", "Services", "Other"])
s_rev = st.sidebar.number_input("Revenue (₹)", min_value=0.0)
s_exp = st.sidebar.number_input("Expense (₹)", min_value=0.0)
s_qty = st.sidebar.number_input("Quantity", min_value=1)

if st.sidebar.button("🚀 Sync to Cloud"):
    data = {"date": str(s_date), "product": s_prod, "revenue": s_rev, "expense": s_exp, "quantity": s_qty, "created_by": st.session_state.user}
    client.table("sales").insert(data).execute()
    st.sidebar.success("Cloud Synchronized!")
    st.rerun()

st.sidebar.divider()
goal = st.sidebar.number_input("Monthly Target (₹)", value=100000)
alert_limit = st.sidebar.slider("Profit Alert Threshold (%)", 5, 30, 15)

# --- DATA ENGINE ---
res = client.table("sales").select("*").execute()
df = pd.DataFrame(res.data)

if not df.empty:
    # Numeric Cleaning
    df["revenue"] = pd.to_numeric(df["revenue"], errors='coerce').fillna(0)
    df["expense"] = pd.to_numeric(df["expense"], errors='coerce').fillna(0)
    df["quantity"] = pd.to_numeric(df["quantity"], errors='coerce').fillna(0)
    df["date"] = pd.to_datetime(df["date"])
    df["profit"] = df["revenue"] - df["expense"]
    df = df.sort_values("date")

    # --- TOP ROW: KPI METRICS ---
    st.title("🏆 AI Business Intelligence")
    t_rev = df["revenue"].sum()
    t_prof = df["profit"].sum()
    margin = (t_prof / t_rev * 100) if t_rev > 0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gross Revenue", f"₹{t_rev:,.0f}")
    c2.metric("Net Profit", f"₹{t_prof:,.0f}", f"{margin:.1f}% Margin")
    c3.metric("Units Sold", int(df["quantity"].sum()))
    c4.metric("Avg Ticket", f"₹{(t_rev/len(df)):,.0f}")

    # --- ALERT SYSTEM ---
    if margin < alert_limit:
        st.error(f"⚠️ ALERT: Margin is {margin:.1f}% (Below {alert_limit}% target!)")
        body = f"Alert: Profit Margin is critical ({margin:.1f}%). Rev: {t_rev}, Prof: {t_prof}."
        mailto = f"mailto:admin@shop.com?subject=Low%20Margin%20Alert&body={body.replace(' ', '%20')}"
        st.markdown(f'<a href="{mailto}" style="padding:8px; background:#FF4B4B; color:white; border-radius:5px; text-decoration:none;">📧 Send Emergency Report</a>', unsafe_content=True)
    else:
        st.success(f"✅ Performance Healthy: Margin ({margin:.1f}%) is above target.")

    # --- GOAL TRACKING ---
    st.subheader("🎯 Monthly Progress")
    progress = min(t_rev / goal, 1.0)
    st.progress(progress)
    st.write(f"Reached *{progress*100:.1f}%* of ₹{goal:,.0f} goal.")

    # --- AI & ANALYTICS ---
    st.divider()
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🤖 AI 7-Day Revenue Forecast")
        daily = df.groupby('date')['revenue'].sum().reset_index()
        daily['day_idx'] = (daily['date'] - daily['date'].min()).dt.days
        if len(daily) > 1:
            model = LinearRegression().fit(daily[['day_idx']], daily['revenue'])
            future = np.array([daily['day_idx'].max() + i for i in range(1, 8)]).reshape(-1, 1)
            preds = model.predict(future)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily['date'], y=daily['revenue'], name="Historical"))
            fig.add_trace(go.Scatter(x=[daily['date'].max() + pd.Timedelta(days=i) for i in range(1, 8)], 
                                     y=preds, name="AI Projection", line=dict(dash='dash', color='orange')))
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("📊 Category Share")
        st.plotly_chart(px.pie(df, values='revenue', names='product', hole=0.4), use_container_width=True)

    # --- AUDIT & EXPORT ---
    st.divider()
    st.subheader("📑 Financial Audit Log")
    st.download_button("📥 Download Data (CSV)", df.to_csv(index=False), "audit_log.csv")
    st.dataframe(df.style.background_gradient(subset=['profit'], cmap='RdYlGn'), use_container_width=True)

else:
    st.info("Awaiting cloud data. Please enter a transaction in the sidebar.")
