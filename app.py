import streamlit as st
from shipper_data import render_shipper_data
from processor import render_processor

# Page Configuration
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
    """Admin Authentication Lock"""
    def password_entered():
        if st.session_state["password_input"] == "ck_admin_2026":
            st.session_state.authenticated = True
            del st.session_state["password_input"]
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
            "SS1: Main Processing (Batch & Single)", 
            "SS3 & SS4: Shipper Management & Mapping Rules"
        ]
    )

    if app_mode == "SS1: Main Processing (Batch & Single)":
        render_processor()
    else:
        # Protected Admin Zone
        if check_password():
            render_shipper_data()

if __name__ == "__main__":
    main()
