import streamlit as st
import tempfile
import os

from main import process_invoice
from exporter import export_to_bytes

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="JAS Extracter",
    layout="wide"
)

# ---------------- CLEAN DARK THEME ----------------
st.markdown("""
<style>

/* MAIN BACKGROUND */
.stApp {
    background-color: #111827;
    color: #F9FAFB;
}

/* TEXT */
h1, h2, h3, h4, h5, h6, label {
    color: #F9FAFB !important;
}

p, span {
    color: #9CA3AF !important;
}

/* FILE UPLOADER FIX */
section[data-testid="stFileUploader"] {
    background-color: #1F2937;
    padding: 15px;
    border-radius: 10px;
}

section[data-testid="stFileUploader"] label {
    color: #F9FAFB !important;
}

section[data-testid="stFileUploader"] div {
    color: #F9FAFB !important;
}

/* INPUT BOXES */
input {
    background-color: #1F2937 !important;
    color: #F9FAFB !important;
    border: 1px solid #374151 !important;
}

/* BUTTON */
.stButton>button {
    background-color: #2563EB;
    color: white;
    border-radius: 6px;
    height: 42px;
    border: none;
}
.stButton>button:hover {
    background-color: #1D4ED8;
}

/* DOWNLOAD BUTTON */
.stDownloadButton>button {
    background-color: #16A34A;
    color: white;
    border-radius: 6px;
    height: 42px;
}

/* ALERT BOXES */
.stAlert {
    background-color: #1F2937 !important;
    color: #F9FAFB !important;
    border-radius: 8px;
}

/* DATAFRAME */
[data-testid="stDataFrame"] {
    background-color: #1F2937;
    border-radius: 8px;
}

/* DIVIDER */
hr {
    border: 1px solid #374151;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<h1>JAS Extracter</h1>
<p style='text-align: center;'>Smart Invoice Extraction for Customs Automation</p>
""", unsafe_allow_html=True)

st.divider()

# ---------------- LAYOUT ----------------
left, right = st.columns([2, 1])

# Upload Section
with left:
    st.subheader("Upload Invoice")

    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

    if uploaded_file:
        st.success("File uploaded successfully")
    else:
        st.info("Upload an Excel file to begin")

# Input Section
with right:
    st.subheader("Shipment Details")

    bl = st.text_input("Bill of Lading")
    ucr = st.text_input("UCR Number")

    process_btn = st.button("Process Invoice", disabled=not uploaded_file)

# ---------------- PROCESS ----------------
st.divider()

if process_btn:
    with st.spinner("Processing invoice..."):

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        try:
            result = process_invoice(
                file_path=tmp_path,
                bill_of_lading=bl,
                ucr=ucr
            )

            df = result["df"]
            csv_bytes = export_to_bytes(df)

            st.success("Processing completed successfully")

            # Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Container Number", result["container_no"])
            m2.metric("Invoice Number", result["invoice_no"])
            m3.metric("Rows Generated", result["row_count"])

            st.divider()

            # Preview
            st.subheader("CSV Preview")
            st.dataframe(df.head(10), use_container_width=True)

            st.divider()

            # Download
            st.download_button(
                label="Download CSV",
                data=csv_bytes,
                file_name=f"{result['container_no']}.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error("Processing failed")
            st.error(str(e))

        finally:
            os.remove(tmp_path)

# ---------------- FOOTER ----------------
st.divider()
st.markdown("""
<p style='text-align:center; color: #9CA3AF;'>
© 2026 JAS Extracter • Logistics Automation System
</p>
""", unsafe_allow_html=True)
