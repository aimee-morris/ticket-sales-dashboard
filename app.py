import streamlit as st
import pandas as pd
import re
from PyPDF2 import PdfReader
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="Multi-Tour Ticket Sales Dashboard", layout="wide")

st.title("📄 Multi-Tour Ticket Sales Dashboard – PDF Reports")

uploaded_files = st.file_uploader("Upload multiple tour report PDFs", type=["pdf"], accept_multiple_files=True)

def extract_metrics_from_pdf(pdf, filename):
    text = ""
    for page in pdf.pages:
        text += page.extract_text() + "\n"

    show_name = filename.replace(".pdf", "").strip()
    data = {"SHOW": show_name}

    try:
        total_tickets = re.search(r"Totals.*?\n(\d{1,3}(?:,\d{3})*)", text)
        gross = re.search(r"£\s*([\d,]+\.\d{2})", text)
        venue_capacity = re.search(r"Venue Capacity\s*\n(\d{1,3}(?:,\d{3})*)", text)
        percent_match = re.search(r"(\d{1,2}\.\d{2})%", text)

        data["Cumulative Sold Tickets"] = int(total_tickets.group(1).replace(",", "")) if total_tickets else None
        data["Cumulative Gross"] = float(gross.group(1).replace(",", "")) if gross else None
        data["Venue Capacity"] = int(venue_capacity.group(1).replace(",", "")) if venue_capacity else None
        data["Capacity Reached (%)"] = float(percent_match.group(1)) if percent_match else None

        # Placeholder values for user input
        data["Cost per Ticket"] = None
        data["Current Spend"] = None
        data["Target Report Date"] = None
        data["Target Tickets"] = None

    except Exception as e:
        st.error(f"Error parsing {filename}: {e}")

    return data

if uploaded_files:
    all_metrics = []
    for uploaded_file in uploaded_files:
        filename = uploaded_file.name.encode('ascii', 'ignore').decode('ascii')
        try:
            pdf = PdfReader(uploaded_file)
            metrics = extract_metrics_from_pdf(pdf, filename)
            all_metrics.append(metrics)
        except Exception as e:
            st.error(f"Could not read {filename}: {e}")

    df = pd.DataFrame(all_metrics)

    st.subheader("📊 Current Tour Metrics")
    st.dataframe(df)

    st.markdown("### 🎯 Add Target Info to Calculate Needs")
    with st.form("target_form"):
        selected_show = st.selectbox("Select a tour to edit target info", df["SHOW"])
        selected_index = df[df["SHOW"] == selected_show].index[0]

        cost_per_ticket = st.number_input("Cost per Ticket (£)", min_value=0.0, value=5.0)
        current_spend = st.number_input("Current Spend (£)", min_value=0.0, value=0.0)
        target_tickets = st.number_input("Target Total Tickets", min_value=0, value=1000)
        target_date = st.date_input("Target Report Date", min_value=datetime.today())

        submitted = st.form_submit_button("Apply Target Info")
        if submitted:
            df.at[selected_index, "Cost per Ticket"] = cost_per_ticket
            df.at[selected_index, "Current Spend"] = current_spend
            df.at[selected_index, "Target Tickets"] = target_tickets
            df.at[selected_index, "Target Report Date"] = pd.to_datetime(target_date)

    # Compute weekly ticket and budget needs
    today = pd.to_datetime(datetime.today())
    df["Target Report Date"] = pd.to_datetime(df["Target Report Date"], errors="coerce")
    df["Remaining Tickets"] = df["Target Tickets"] - df["Cumulative Sold Tickets"]
    df["Days Remaining"] = (df["Target Report Date"] - today).dt.days
    df["Weeks Remaining"] = (df["Days Remaining"] / 7).round(1)
    df["Weekly Ticket Target"] = (df["Remaining Tickets"] / df["Weeks Remaining"]).round(1)
    df["Extra Budget Needed"] = df["Remaining Tickets"] * df["Cost per Ticket"]

    st.markdown("### 📈 Target Calculations")
    st.dataframe(df[[
        "SHOW", "Cumulative Sold Tickets", "Venue Capacity", "Capacity Reached (%)",
        "Target Tickets", "Target Report Date", "Weekly Ticket Target", "Extra Budget Needed"
    ]].dropna(subset=["Target Tickets"]))
else:
    st.info("Upload multiple PDF reports to get started.")
