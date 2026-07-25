"""
frontend/app.py
----------------
Streamlit dashboard for the AML Suspicious Activity Detection Agent.

Pages (sidebar navigation):
  Dashboard, Upload Dataset, Chat, Suspicious Transactions,
  Customer Details, Network Graph, Analytics, Settings

All pages talk to the FastAPI backend over HTTP — no business logic lives
here, keeping the UI a thin client over the agent.
"""

import os
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AML Suspicious Activity Agent", layout="wide", page_icon="🕵️")

if "dataset_id" not in st.session_state:
    st.session_state.dataset_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ---------------------------------------------------------------- helpers
def api_get(path, **params):
    r = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def api_post(path, json=None, files=None, params=None):
    r = requests.post(f"{BACKEND_URL}{path}", json=json, files=files, params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def require_dataset():
    if not st.session_state.dataset_id:
        st.warning("Please upload a dataset first on the **Upload Dataset** page.")
        st.stop()


# ---------------------------------------------------------------- sidebar
st.sidebar.title("🕵️ AML Agent")
page = st.sidebar.radio("Navigate", [
    "Dashboard", "Upload Dataset", "Chat", "Suspicious Transactions",
    "Customer Details", "Network Graph", "Analytics", "Settings",
])
if st.session_state.dataset_id:
    st.sidebar.success(f"Active dataset: {st.session_state.dataset_id}")
else:
    st.sidebar.info("No dataset uploaded yet.")


# ---------------------------------------------------------------- Upload
if page == "Upload Dataset":
    st.title("📤 Upload Transaction Dataset")
    st.markdown("Upload a CSV with columns: `transaction_id, customer_id, timestamp, amount, "
                "beneficiary_id, country, channel`.")

    uploaded = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded is not None and st.button("Upload & Validate"):
        try:
            resp = api_post("/upload", files={"file": (uploaded.name, uploaded.getvalue(), "text/csv")})
            st.session_state.dataset_id = resp["dataset_id"]
            st.success(f"Uploaded {resp['rows']} rows. Dataset ID: {resp['dataset_id']}")
            st.json(resp)
        except requests.HTTPError as e:
            st.error(f"Upload failed: {e.response.json().get('detail', str(e))}")

    st.markdown("---")
    st.markdown("Don't have data handy? Use `sample_data/transactions.csv` from the project root.")


# ---------------------------------------------------------------- Dashboard
elif page == "Dashboard":
    st.title("📊 Dashboard")
    require_dataset()

    if st.button("Run Full Risk Pipeline"):
        with st.spinner("Running features -> rules -> ML -> risk scoring -> explanations..."):
            st.session_state.risk_report = api_post("/risk-report", params={"dataset_id": st.session_state.dataset_id})

    report = st.session_state.get("risk_report")
    if report:
        risk_rows = report.get("risk_score", {}).get("risk_report", [])
        df_risk = pd.DataFrame(risk_rows)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Customers Scored", len(df_risk))
        col2.metric("High Risk", int((df_risk["risk_level"] == "High").sum()) if not df_risk.empty else 0)
        col3.metric("Medium Risk", int((df_risk["risk_level"] == "Medium").sum()) if not df_risk.empty else 0)
        col4.metric("Low Risk", int((df_risk["risk_level"] == "Low").sum()) if not df_risk.empty else 0)

        if not df_risk.empty:
            fig = px.pie(df_risk, names="risk_level", title="Risk Level Breakdown",
                          color="risk_level",
                          color_discrete_map={"High": "#d62728", "Medium": "#ff7f0e", "Low": "#2ca02c"})
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Top Suspicious Customers")
            st.dataframe(df_risk.head(10)[["customer_id", "final_score", "risk_level", "rule_score", "ml_score"]],
                         use_container_width=True)

        explanations = report.get("explanation", {}).get("explanations", [])
        if explanations:
            st.subheader("🔎 Explanations (Top Flagged Customers)")
            for e in explanations:
                with st.expander(f"Customer {e['customer_id']} — {e['risk_level']} ({e['final_score']})"):
                    st.write(e["explanation"])
    else:
        st.info("Click **Run Full Risk Pipeline** to populate the dashboard.")


# ---------------------------------------------------------------- Chat
elif page == "Chat":
    st.title("💬 Ask the Agent")
    require_dataset()
    st.caption("Try: 'Find suspicious customers', 'Show structuring', 'Average transaction amount', "
               "'Explain customer 123'")

    query = st.chat_input("Ask about the transaction data...")
    for turn in st.session_state.chat_history:
        with st.chat_message(turn["role"]):
            st.write(turn["content"])

    if query:
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.write(query)

        with st.chat_message("assistant"):
            with st.spinner("Planning and executing tools..."):
                resp = api_post("/chat", json={"query": query, "dataset_id": st.session_state.dataset_id})
            plan = resp["plan"]
            st.caption(f"🧠 Intent: `{plan['intent']}` | Tools used: `{plan['tools']}` | "
                       f"Source: {plan['source']}")
            st.caption(plan["reasoning"])

            results = resp["results"]
            if "explanation" in results:
                for e in results["explanation"]["explanations"]:
                    st.markdown(f"**Customer {e['customer_id']} — {e['risk_level']}**: {e['explanation']}")
            elif "eda" in results:
                st.json(results["eda"]["transaction_stats"])
            elif "risk_score" in results:
                st.dataframe(pd.DataFrame(results["risk_score"]["risk_report"]))
            else:
                st.json(results)

            st.session_state.chat_history.append({"role": "assistant", "content": "See results above."})


# ---------------------------------------------------------------- Suspicious Transactions
elif page == "Suspicious Transactions":
    st.title("🚩 Suspicious Transactions")
    require_dataset()

    if st.button("Detect Suspicious Activity"):
        with st.spinner("Running rule engine + ML..."):
            st.session_state.risk_report = api_post("/risk-report", params={"dataset_id": st.session_state.dataset_id})

    report = st.session_state.get("risk_report")
    if report:
        rows = report.get("risk_score", {}).get("risk_report", [])
        df_risk = pd.DataFrame(rows)
        level_filter = st.multiselect("Filter by risk level", ["High", "Medium", "Low"], default=["High", "Medium"])
        if not df_risk.empty:
            filtered = df_risk[df_risk["risk_level"].isin(level_filter)]
            st.dataframe(filtered, use_container_width=True)
    else:
        st.info("Click the button above to run detection.")


# ---------------------------------------------------------------- Customer Details
elif page == "Customer Details":
    st.title("👤 Customer Details")
    require_dataset()

    customer_id = st.text_input("Customer ID")
    if customer_id and st.button("Look up customer"):
        with st.spinner("Fetching customer profile..."):
            data = api_get(f"/customer/{customer_id}", dataset_id=st.session_state.dataset_id)

        st.subheader("Statistics")
        st.json(data.get("customer_stats", {}))

        st.subheader("Risk Score")
        risk = data.get("risk_score", {}).get("risk_report", [])
        st.json(risk[0] if risk else "No risk data for this customer.")

        st.subheader("Explanation")
        exp = data.get("explanation", {}).get("explanations", [])
        if exp:
            st.write(exp[0]["explanation"])


# ---------------------------------------------------------------- Network Graph
elif page == "Network Graph":
    st.title("🕸️ Transaction Network Graph")
    require_dataset()

    customer_id = st.text_input("Center on Customer ID")
    hops = st.slider("Hops", 1, 3, 1)
    if customer_id and st.button("Build Graph"):
        with st.spinner("Building transaction graph..."):
            data = api_get(f"/graph/{customer_id}", dataset_id=st.session_state.dataset_id, hops=hops)

        G = nx.DiGraph()
        for n in data["nodes"]:
            G.add_node(n)
        for e in data["edges"]:
            G.add_edge(e["source"], e["target"], weight=e["amount"])

        pos = nx.spring_layout(G, seed=42)
        edge_x, edge_y = [], []
        for u, v in G.edges():
            edge_x += [pos[u][0], pos[v][0], None]
            edge_y += [pos[u][1], pos[v][1], None]

        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color="#888"), mode="lines")
        node_x = [pos[n][0] for n in G.nodes()]
        node_y = [pos[n][1] for n in G.nodes()]
        node_trace = go.Scatter(
            x=node_x, y=node_y, mode="markers+text", text=list(G.nodes()), textposition="top center",
            marker=dict(size=16, color=["#d62728" if n == customer_id else "#1f77b4" for n in G.nodes()]),
        )
        fig = go.Figure(data=[edge_trace, node_trace])
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------- Analytics
elif page == "Analytics":
    st.title("📈 Analytics")
    require_dataset()

    eda_data = api_post("/eda", json={"dataset_id": st.session_state.dataset_id})
    st.subheader("Transaction Statistics")
    st.json(eda_data["transaction_stats"])

    st.subheader("Amount Distribution")
    hist = eda_data["distribution"]["amount_histogram"]
    fig = px.bar(x=hist["bin_edges"][:-1], y=hist["counts"], labels={"x": "Amount", "y": "Count"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Daily Transaction Volume")
    daily = eda_data["distribution"]["daily_txn_counts"]
    fig2 = px.line(x=daily["dates"], y=daily["counts"], labels={"x": "Date", "y": "Transactions"})
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Missing Values")
    st.json(eda_data["missing_values"])


# ---------------------------------------------------------------- Settings
elif page == "Settings":
    st.title("⚙️ Settings")
    st.text_input("Backend URL", value=BACKEND_URL, disabled=True,
                  help="Set BACKEND_URL as an environment variable to change this.")
    st.markdown("LLM provider, model name, and API key are configured via the `.env` file "
                "(see `.env.example`). Restart the backend after changing them.")
    if st.button("Check backend health"):
        try:
            st.json(api_get("/health"))
        except Exception as e:
            st.error(f"Backend unreachable: {e}")
