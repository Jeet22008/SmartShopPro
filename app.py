import streamlit as st
import pandas as pd
import plotly.express as px
from postgrest import SyncPostgrestClient
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. PAGE CONFIG (Must be the very first Streamlit command)
st.set_page_config(page_title="SmartShop Pro Cloud", layout="wide")

# 2. CLOUD CONNECTION
# These keys are pulled from your .streamlit/secrets.toml file
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

# Postgrest needs the /rest/v1 suffix to talk to your Supabase database
client = SyncPostgrestClient(f"{url}/rest/v1", headers={
    "apikey": key, 
    "Authorization": f"Bearer {key}"
})

# --- AUTHENTICATION SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 SmartShop Cloud Login")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        u = st.text_input("Username", key="l_user")
        p = st.text_input("Password", type="password", key="l_pw")
        if st.button("Login"):
            # Check if user exists in the cloud 'users' table
            res = client.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tab2:
        new_u = st.text_input("Choose Username", key="s_user")
        new_p = st.text_input("Choose Password", type="password", key="s_pw")
        if st.button("Create Account"):
            client.table("users").insert({"username": new_u, "password": new_p}).execute()
            st.success("Account created! You can now log in on the Login tab.")
    st.stop()

# --- MAIN DASHBOARD (Only visible after login) ---
st.title("📊 SmartShop Pro - Cloud Dashboard")

# Sidebar: Add Sales to the Cloud
st.sidebar.header("Add New Sale")
s_date = st.sidebar.date_input("Date")
s_prod = st.sidebar.text_input("Product")
s_rev = st.sidebar.number_input("Revenue (₹)", min_value=0.0)
s_exp = st.sidebar.number_input("Expense (₹)", min_value=0.0)
s_qty = st.sidebar.number_input("Quantity", min_value=0)

if st.sidebar.button("Push to Cloud"):
    data = {"date": str(s_date), "product": s_prod, "revenue": s_rev, "expense": s_exp, "quantity": s_qty}
    client.table("sales").insert(data).execute()
    st.sidebar.success("Sale Saved to Cloud!")
    st.rerun()

# Data Loading from Supabase
res = client.table("sales").select("*").execute()
df = pd.DataFrame(res.data)

if df.empty:
    st.info("Cloud database is empty. Add data using the sidebar.")
else:
    df["date"] = pd.to_datetime(df["date"])
    df["profit"] = df["revenue"] - df["expense"]
    
    # KPI Cards
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"₹{df['revenue'].sum():,.0f}")
    col2.metric("Total Profit", f"₹{df['profit'].sum():,.0f}")
    col3.metric("Items Sold", df["quantity"].sum())

    # Visualizations
    st.subheader("📈 Revenue Trend")
    trend = df.groupby("date")["revenue"].sum().reset_index()
    fig = px.line(trend, x="date", y="revenue", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    # Data Management (Delete)
    st.divider()
    st.subheader("🗑️ Manage Records")
    row_id = st.selectbox("Select Record ID to Delete", df["id"].tolist())
    if st.button("Delete Selected Record", type="primary"):
        client.table("sales").delete().eq("id", row_id).execute()
        st.success(f"Record {row_id} deleted!")
        st.rerun()