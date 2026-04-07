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

/* Background */
.stApp {
    background-color: #111827;
    color: #F9FAFB;
}

/* Section spacing */
.block-container {
    padding-top: 2rem;
}

/* Headers */
h1 {
    text-align: center;
    font-weight: 600;
}
h2, h3 {
    color: #F9FAFB;
}

/* Subtext */
p {
    color: #9CA3AF;
}

/* Buttons */
.stButton>button {
    background-color: #2563EB;
    color: white;
    border-radius: 6px;
    height: 42px;
    border: none;
    font-weight: 500;
}
.stButton>button:hover {
    background-color: #1D4ED8;
}

/* Download button */
.stDownloadButton>button {
    background-color: #16A34A;
    color: white;
    border-radius: 6px;
    height: 42px;
    border: none;
}

/* Inputs */
input {
    background-color: #1F2937 !important;
    color: #F9FAFB !important;
}

/* Divider */
hr {
    border: 1px solid #374151;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    background-color: #1F2937;
    border-radius: 8px;
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
