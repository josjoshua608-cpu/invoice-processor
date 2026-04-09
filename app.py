import streamlit as st
import tempfile
import os

from main import process_invoice
from exporter import export_to_bytes

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Global Customs Platform",
    page_icon="🌍",
    layout="wide"
)

# ---------------- GLOBAL UI STYLING ----------------
st.markdown("""
<style>

.stApp {
    background-color: #f7f9fc;
}

h1 {
    font-size: 34px !important;
    font-weight: 700;
    color: #1f2937;
}

h2, h3 {
    color: #374151;
}

.block-container {
    padding-top: 2rem;
}

/* Upload box */
[data-testid="stFileUploader"] {
    border: 2px dashed #cbd5e1;
    border-radius: 12px;
    padding: 20px;
    background: white;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #4f46e5, #6366f1);
    color: white;
    border-radius: 10px;
    height: 45px;
    font-weight: 600;
    border: none;
}

/* Download Button */
.stDownloadButton > button {
    background: #10b981;
    color: white;
    border-radius: 10px;
    height: 45px;
    font-weight: 600;
}

/* Metrics cards */
[data-testid="stMetric"] {
    background: white;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0px 2px 10px rgba(0,0,0,0.05);
}

/* Data editor */
[data-testid="stDataEditor"] {
    background: white;
    border-radius: 12px;
    padding: 10px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<div style='text-align:center; margin-bottom:20px;'>

<h1>🌍 Global Customs Automation Platform</h1>

<p style='color:#6b7280; font-size:16px;'>
Convert invoices into structured customs declarations — fast, accurate, and compliant
</p>

</div>
""", unsafe_allow_html=True)

st.divider()

# ---------------- MAIN LAYOUT ----------------
col1, col2 = st.columns([2, 1])

# LEFT SIDE (UPLOAD)
with col1:
    st.subheader("📁 Upload Invoice")

    uploaded_file = st.file_uploader(
        "Upload your Excel file",
        type=["xlsx"]
    )

    if uploaded_file:
        st.success(f"✅ {uploaded_file.name} uploaded successfully")

# RIGHT SIDE (INPUTS)
with col2:
    st.subheader("⚙️ Shipment Details")

    bl = st.text_input("Bill of Lading (BL)", placeholder="Enter BL number")
    ucr = st.text_input("UCR Number", placeholder="Enter UCR")

    process_btn = st.button("🚀 Generate Customs Data", use_container_width=True)

# ---------------- PROCESS ----------------
st.divider()

# Session state init
if "processed" not in st.session_state:
    st.session_state.processed = False

if process_btn:
    if not uploaded_file:
        st.error("❌ Please upload an Excel file first")
    else:
        with st.spinner("⏳ Processing invoice... Please wait"):

            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                result = process_invoice(
                    file_path=tmp_path,
                    bill_of_lading=bl,
                    ucr=ucr
                )

                st.session_state.processed = True
                st.session_state.original_df = result["df"]
                st.session_state.container_no = result["container_no"]
                st.session_state.invoice_no = result["invoice_no"]
                st.session_state.row_count = result["row_count"]

            except Exception as e:
                st.error("❌ Processing Failed")
                st.error(str(e))

            finally:
                os.remove(tmp_path)

# ---------------- SHOW RESULT ----------------
if st.session_state.processed:

    st.markdown("""
    <div style='padding:10px; background:#ecfdf5; border-radius:10px; color:#065f46; font-weight:600;'>
    ✅ Data Processed Successfully • Ready for Review
    </div>
    """, unsafe_allow_html=True)

    # METRICS
    m1, m2, m3 = st.columns(3)
    m1.metric("📦 Container No", st.session_state.container_no)
    m2.metric("🧾 Invoice No", st.session_state.invoice_no)
    m3.metric("📊 Rows Generated", st.session_state.row_count)

    st.divider()

    # ---------------- PREVIEW ----------------
    st.subheader("📊 Data Review & Validation")

    # Remove duplicate columns
    clean_df = st.session_state.original_df.loc[:, ~st.session_state.original_df.columns.duplicated()]

    # Remove Artikelcode value for UI clarity
    if "Artikelcode" in clean_df.columns:
        clean_df["Artikelcode"] = ""

    edited_df = st.data_editor(
        clean_df,
        use_container_width=True,
        num_rows="dynamic"
    )

    st.session_state.final_df = edited_df

    # ---------------- EXPORT ----------------
    csv_bytes = export_to_bytes(st.session_state.final_df)

    st.download_button(
        label="⬇️ Download CSV File",
        data=csv_bytes,
        file_name=f"{st.session_state.container_no}.csv",
        mime="text/csv",
        use_container_width=True
    )

# ---------------- FOOTER ----------------
st.divider()
st.markdown(
    "<p style='text-align:center; color: grey;'>Built for Customs Automation • Professional Tool</p>",
    unsafe_allow_html=True
)
