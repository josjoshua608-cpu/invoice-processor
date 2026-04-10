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

# ---------------- HEADER ----------------
st.markdown("""
<h1 style='text-align: center;'>🌍 Global Customs Platform</h1>
<p style='text-align: center; color: gray;'>Upload invoice → Extract → Export CSV</p>
""", unsafe_allow_html=True)

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader(
    "📂 Upload Invoice (.xlsx)",
    type=["xlsx"]
)

if uploaded_file:

    st.success(f"File uploaded: {uploaded_file.name}")

    if st.button("🚀 Process Invoice"):

        with st.spinner("Processing invoice..."):

            # Save temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                # ---------------- RUN PIPELINE ----------------
                result = process_invoice(
                    file_path=tmp_path,
                    output_dir="output"
                )

                df = result["df"]

                # ---------------- UI FRIENDLY COLUMNS ----------------
                df_ui = df.rename(columns={
                    "Artikelcode": "HS Code",
                    "Goederenomschrijving": "Description",
                    "Aantal": "Package Total",
                    "Bruto (kg)": "Gross Weight",
                    "Netto (kg)": "Net Weight",
                    "Prijs van goederen": "Total Value",
                    "Valuta": "Currency",
                    "Land van oorsprong": "Country of Origin",
                })

                # ---------------- METRICS ----------------
                col1, col2, col3 = st.columns(3)

                col1.metric("📦 Total Rows", len(df_ui))
                col2.metric("📄 Invoice No", result["invoice_no"] or "-")
                col3.metric("🚢 Container", result["container_no"] or "-")

                st.divider()

                # ---------------- TABLE ----------------
                st.subheader("📊 Processed Data")
                st.dataframe(df_ui, use_container_width=True)

                # ---------------- DOWNLOAD ----------------
                csv_bytes = export_to_bytes(df)

                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_bytes,
                    file_name=f"{result['container_no'] or 'output'}.csv",
                    mime="text/csv"
                )

                st.success("✅ Processing Completed")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

else:
    st.info("Please upload an invoice file to begin.")
