import streamlit as st
import tempfile
import os

from main import process_invoice
from exporter import export_to_bytes

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Invoice Processor",
    page_icon="📊",
    layout="wide"
)

# ---------------- HEADER ----------------
st.markdown("""
    <h1 style='text-align: center;'>📊 Invoice to Customs CSV Converter</h1>
    <p style='text-align: center; color: grey;'>
        Convert Excel invoices into 82-column Dutch customs CSV format
    </p>
""", unsafe_allow_html=True)

st.divider()

# ---------------- MAIN LAYOUT ----------------
col1, col2 = st.columns([2, 1])

# LEFT SIDE (UPLOAD + PREVIEW)
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
    st.subheader("⚙️ Input Details")

    bl = st.text_input("Bill of Lading (BL)", placeholder="Enter BL number")
    ucr = st.text_input("UCR Number", placeholder="Enter UCR")

    process_btn = st.button("🚀 Process Invoice", use_container_width=True)

# ---------------- PROCESS ----------------
st.divider()

# ✅ ADDED: persistent state flags
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

                # ✅ STORE EVERYTHING IN SESSION
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

# ✅ SHOW UI IF ALREADY PROCESSED (THIS FIXES DISAPPEAR ISSUE)
if st.session_state.processed:

    st.success("✅ Processing Completed Successfully!")

    # METRICS
    m1, m2, m3 = st.columns(3)
    m1.metric("📦 Container No", st.session_state.container_no)
    m2.metric("🧾 Invoice No", st.session_state.invoice_no)
    m3.metric("📊 Rows Generated", st.session_state.row_count)

    st.divider()

    # ---------------- PREVIEW ----------------
    st.subheader("📊 Preview & Edit Data")

    # Remove duplicate columns ONLY for preview
    clean_df = st.session_state.original_df.loc[:, ~st.session_state.original_df.columns.duplicated()]

    edited_df = st.data_editor(
        clean_df,
        use_container_width=True,
        num_rows="dynamic"
    )

    # store edited version
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
