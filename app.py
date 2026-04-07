import streamlit as st
import tempfile
import os

from main import process_invoice
from exporter import export_to_bytes

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="JAS Extracter",
    page_icon="🚢",
    layout="wide"
)

# ---------------- CUSTOM STYLING ----------------
st.markdown("""
<style>
.main {
    padding-top: 1rem;
}
.block-container {
    padding-top: 2rem;
}
.stButton>button {
    background-color: #1f77b4;
    color: white;
    border-radius: 8px;
    height: 3em;
    width: 100%;
}
.stDownloadButton>button {
    background-color: #2ca02c;
    color: white;
    border-radius: 8px;
    height: 3em;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
    <h1 style='text-align: center;'>🚢 JAS Extracter</h1>
    <p style='text-align: center; color: grey; font-size:16px;'>
        Smart Invoice Extraction for Customs Automation
    </p>
""", unsafe_allow_html=True)

st.divider()

# ---------------- INSTRUCTIONS ----------------
with st.expander("ℹ️ How to Use"):
    st.markdown("""
    1. Upload your invoice Excel file  
    2. Enter Bill of Lading (optional)  
    3. Enter UCR (optional)  
    4. Click **Process Invoice**  
    5. Download your CSV file  
    """)

# ---------------- MAIN LAYOUT ----------------
left, right = st.columns([2, 1])

# LEFT: Upload Section
with left:
    st.subheader("📁 Upload Invoice")

    uploaded_file = st.file_uploader(
        "Drag & drop or browse your Excel file",
        type=["xlsx"]
    )

    if uploaded_file:
        st.success(f"✅ File uploaded: {uploaded_file.name}")
    else:
        st.info("Upload an Excel invoice to begin")

# RIGHT: Input Section
with right:
    st.subheader("⚙️ Shipment Details")

    bl = st.text_input("Bill of Lading", placeholder="Optional")
    ucr = st.text_input("UCR Number", placeholder="Optional")

    process_btn = st.button(
        "🚀 Process Invoice",
        disabled=not uploaded_file
    )

# ---------------- PROCESS ----------------
st.divider()

if process_btn:
    with st.spinner("⏳ Processing your invoice..."):

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

            # SUCCESS MESSAGE
            st.success("✅ Processing Completed Successfully!")

            # METRICS
            m1, m2, m3 = st.columns(3)
            m1.metric("📦 Container No", result["container_no"])
            m2.metric("🧾 Invoice No", result["invoice_no"])
            m3.metric("📊 Rows Generated", result["row_count"])

            st.divider()

            # PREVIEW
            st.subheader("📄 CSV Preview (Top 10 Rows)")
            st.dataframe(df.head(10), use_container_width=True)

            st.divider()

            # DOWNLOAD
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_bytes,
                file_name=f"{result['container_no']}.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error("❌ Processing Failed")
            st.error(str(e))

        finally:
            os.remove(tmp_path)

# ---------------- FOOTER ----------------
st.divider()
st.markdown("""
<p style='text-align:center; color: grey;'>
© 2026 JAS Extracter • Built for Logistics & Export Industry
</p>
""", unsafe_allow_html=True)
