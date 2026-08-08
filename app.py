import streamlit as st
import os

# Page configuration
st.set_page_config(
    page_title="CK PDF PROCESSOR",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State for Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    """Returns True if the user entered the correct admin password."""
    def password_entered():
        # Simple hardcoded check for demo; can be moved to config.py or secrets.toml
        if st.session_state["password_input"] == "ck_admin_2026":
            st.session_state.authenticated = True
            del st.session_state["password_input"]  # don't store password
        else:
            st.session_state.authenticated = False
            st.error("😕 Incorrect password")

    if not st.session_state.authenticated:
        st.subheader("🔐 Admin Authentication Required")
        st.text_input(
            "Enter Admin Password", 
            type="password", 
            on_change=password_entered, 
            key="password_input"
        )
        return False
    return True

def main():
    st.title("📄 CK PDF PROCESSOR")
    st.markdown("---")

    # Sidebar Navigation
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.selectbox(
        "Choose Mode",
        [
            "SS1: Main Processing", 
            "SS3: Header Mapping Rules", 
            "SS4: Item Table Column Builder", 
            "SS5: Universal Debugger & Test Suite", 
            "SS6: Shipper Management"
        ]
    )

    if app_mode == "SS1: Main Processing":
        render_main_processing()
    else:
        # Protected Admin Routes
        if check_password():
            if app_mode == "SS3: Header Mapping Rules":
                import modules.ss3_header_mapping as ss3
                ss3.render()
            elif app_mode == "SS4: Item Table Column Builder":
                import modules.ss4_table_builder as ss4
                ss4.render()
            elif app_mode == "SS5: Universal Debugger & Test Suite":
                import modules.ss5_debugger as ss5
                ss5.render()
            elif app_mode == "SS6: Shipper Management":
                import modules.ss6_shipper_manager as ss6
                ss6.render()

def render_main_processing():
    st.header("🚀 Batch Invoice Processing (SS1)")
    st.write("Upload standardized invoice PDFs or Excel files, select your shipper, and process in batch.")

    # Shipper Selection (Placeholder for dynamic list loaded from GitHub/JSON)
    shippers_list = ["Welspun India", "BKT Tyres", "Select Shipper..."]
    selected_shipper = st.selectbox("Select Active Shipper", shippers_list)

    uploaded_files = st.file_uploader(
        "Upload PDF/Excel Invoices", 
        type=["pdf", "xlsx", "xls"], 
        accept_multiple_files=True
    )

    if uploaded_files and selected_shipper != "Select Shipper...":
        st.success(f"Loaded {len(uploaded_files)} file(s) ready for processing under shipper: **{selected_shipper}**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Process & Download Excel"):
                st.info("Batch processing simulation: Excel generation logic will be executed here.")
        with col2:
            if st.button("Process & Push to Google Sheets"):
                st.info("Batch processing simulation: Google Sheets API push logic will be executed here.")

if __name__ == "__main__":
    main()
