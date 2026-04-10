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

# ---------------- STYLING ----------------
st.markdown("""
<style>
.stApp { background-color: #f7f9fc; }
h1 { font-size: 34px !important; font-weight: 700; color: #1f2937; }
[data-testid="stMetric"] {
    background: white; padding: 15px; border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 👤 HARDCODED USERS  ← Change these!
# ─────────────────────────────────────────────
USERS = {
    "admin": "admin123",
    "user1": "password1",
}

# ---------------- SESSION INIT ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "processed" not in st.session_state:
    st.session_state.processed = False

# ─────────────────────────────────────────────
# 🔐 LOGIN PAGE
# ─────────────────────────────────────────────
def login_page():
    st.markdown("""
        <div style='text-align:center; margin-top: 80px;'>
            <h1>🔐 Login</h1>
            <p style='color:#6b7280;'>Enter your credentials to access the platform</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")

        if st.button("Login", use_container_width=True, type="primary"):
            if username in USERS and USERS[username] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

# ─────────────────────────────────────────────
# 🌍 MAIN APP
# ─────────────────────────────────────────────
def main_app():
    # ---------------- LOGOUT BUTTON ----------------
    st.sidebar.markdown(f"👤 Logged in as **{st.session_state.username}**")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.processed = False
        st.rerun()

    # ---------------- HEADER ----------------
    st.markdown("""
    <div style='text-align:center;'>
    <h1>🌍 Global Customs Automation Platform</h1>
    <p style='color:#6b7280;'>Fast • Accurate • Compliant</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # ---------------- LAYOUT ----------------
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload Excel", type=["xlsx"])
    with col2:
        bl = st.text_input("BL Number")
        ucr = st.text_input("UCR")
        process_btn = st.button("🚀 Process Invoice", use_container_width=True)
    st.divider()

    # ---------------- PROCESS ----------------
    if process_btn:
        if not uploaded_file:
            st.error("Upload file first")
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            try:
                result = process_invoice(tmp_path, bl, ucr)
                st.session_state.processed = True
                st.session_state.original_df = result["df"].copy()
                st.session_state.container_no = result["container_no"]
                st.session_state.invoice_no = result["invoice_no"]
                st.session_state.row_count = result["row_count"]
            finally:
                os.remove(tmp_path)

    # ---------------- DISPLAY ----------------
    if st.session_state.processed:
        st.success("Processing Completed")
        m1, m2, m3 = st.columns(3)
        m1.metric("Container", st.session_state.container_no)
        m2.metric("Invoice", st.session_state.invoice_no)
        m3.metric("Rows", st.session_state.row_count)
        st.divider()

        # ---------------- PREVIEW ----------------
        st.subheader("📊 Preview & Edit")
        original_df = st.session_state.original_df

        clean_df = original_df.loc[:, ~original_df.columns.duplicated()].copy()
        if "Artikelcode" in clean_df.columns:
            clean_df["Artikelcode"] = ""
        edited_df = st.data_editor(
            clean_df,
            use_container_width=True,
            num_rows="dynamic"
        )

        # ---------------- APPLY EDITS BACK ----------------
        final_df = original_df.copy()
        for col in edited_df.columns:
            if col in final_df.columns:
                final_df[col] = edited_df[col]

        # ---------------- EXPORT ----------------
        csv_bytes = export_to_bytes(final_df)
        st.download_button(
            "⬇️ Download CSV",
            data=csv_bytes,
            file_name=f"{st.session_state.container_no}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # ---------------- FOOTER ----------------
    st.divider()
    st.markdown(
        "<p style='text-align:center; color: grey;'>Customs Automation Tool</p>",
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────
if st.session_state.logged_in:
    main_app()
else:
    login_page()
