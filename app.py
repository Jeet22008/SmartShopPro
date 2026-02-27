import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from postgrest import SyncPostgrestClient
from sklearn.linear_model import LinearRegression
import numpy as np

# 1. PAGE SETUP
st.set_page_config(page_title="SmartShop Pro AI", layout="wide", page_icon="📈")

# 2. DATABASE CONNECTION
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    client = SyncPostgrestClient(f"{url}/rest/v1", headers={"apikey": key, "Authorization": f"Bearer {key}"})
except Exception:
    st.error("Secrets not found! Add SUPABASE_URL and SUPABASE_KEY in Streamlit Cloud Settings.")
    st.stop()

# 3. SIDEBAR - DATA ENTRY
st.sidebar.title("📑 Data Entry")
s_date = st.sidebar.date_input("Transaction Date")
s_prod = st.sidebar.selectbox("Product Category", ["Electronics", "Grocery", "Apparel", "Services"])
s_rev = st.sidebar.number_input("Revenue (₹)", min_value=0.0, format="%.2f")
s_exp = st.sidebar.number_input("Expense (₹)", min_value=0.0, format="%.2f")
s_qty = st.sidebar.number_input("Quantity Sold", min_value=1)

if st.sidebar.button("🚀 Push to Cloud"):
    # CRITICAL: Column names here MUST match your Supabase table exactly
    new_data = {
        "date": str(s_date),
        "product": s_prod,
        "revenue": float(s_rev),
        "expense": float(s_exp),
        "quantity": int(s_qty)
    }
    try:
        client.table("sales").insert(new_data).execute()
        st.sidebar.success("Successfully Synced!")
        st.rerun()
    except Exception as e:
        st.sidebar.error("Sync Failed. Verify your Supabase table has: date, product, revenue, expense, quantity.")

# 4. DATA ENGINE & ANALYTICS
res = client.table("sales").select("*").execute()
df = pd.DataFrame(res.data)

if not df.empty:
    # Data Cleaning
    df["revenue"] = pd.to_numeric(df["revenue"], errors='coerce').fillna(0)
    df["expense"] = pd.to_numeric(df["expense"], errors='coerce').fillna(0)
    df["quantity"] = pd.to_numeric(df["quantity"], errors='coerce').fillna(0)
    df["date"] = pd.to_datetime(df["date"])
    df["profit"] = df["revenue"] - df["expense"]
    df = df.sort_values("date")

    # 5. KPI DASHBOARD
    st.title("🏛️ AI Business Intelligence")
    
    t_rev = df["revenue"].sum()
    t_prof = df["profit"].sum()
    margin = (t_prof / t_rev * 100) if t_rev > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Revenue", f"₹{t_rev:,.0f}")
    c2.metric("Net Profit", f"₹{t_prof:,.0f}", f"{margin:.1f}% Margin")
    c3.metric("Items Sold", int(df["quantity"].sum()))

    # 6. AI FORECASTING
    st.divider()
    daily = df.groupby('date')['revenue'].sum().reset_index()
    if len(daily) > 1:
        daily['day_idx'] = (daily['date'] - daily['date'].min()).dt.days
        model = LinearRegression().fit(daily[['day_idx']], daily['revenue'])
        future_idx = np.array([daily['day_idx'].max() + i for i in range(1, 8)]).reshape(-1, 1)
        preds = model.predict(future_idx)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily['date'], y=daily['revenue'], name="Actual Sales"))
        fig.add_trace(go.Scatter(x=[daily['date'].max() + pd.Timedelta(days=i) for i in range(1, 8)], 
                                 y=preds, name="AI Prediction", line=dict(dash='dash', color='orange')))
        st.plotly_chart(fig, use_container_width=True)

    # 7. AUDIT LOG
    st.divider()
    st.subheader("📑 Transaction History")
    st.dataframe(df.style.background_gradient(subset=['profit'], cmap='RdYlGn'), use_container_width=True)
else:
    st.warning("Awaiting first entry. Use the sidebar to add a sale.")
