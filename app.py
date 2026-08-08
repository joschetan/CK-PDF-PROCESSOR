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

def main():
    st.title("📄 CK PDF PROCESSOR")
    st.markdown("---")

    # 1. Main Processing Zone (SS1) - हमेशा सबसे पहले दिखेगा
    render_processor()

    st.markdown("---")
    
    # 2. Main Page के बिल्कुल नीचे Admin Login & Configuration Zone
    st.subheader("🔐 Admin & Shipper Configuration Zone")
    
    if not st.session_state.authenticated:
        st.info("⚠️ कॉन्फ़िगरेशन और मैपिंग रूल्स बदलने के लिए एडमिन पासवर्ड दर्ज करें।")
        
        def password_entered():
            if st.session_state["password_input"] == "ck_admin_2026":
                st.session_state.authenticated = True
                del st.session_state["password_input"]
            else:
                st.session_state.authenticated = False
                st.error("😕 गलत पासवर्ड! कृपया सही पासवर्ड दर्ज करें।")

        st.text_input(
            "Enter Admin Password", 
            type="password", 
            on_change=password_entered, 
            key="password_input"
        )
    else:
        st.success("🔓 Admin Access Granted (सफलतापूर्वक लॉग इन हैं)")
        
        if st.button("🔒 Logout Admin"):
            st.session_state.authenticated = False
            st.rerun()
            
        st.markdown("---")
        # यहाँ एडमिन शिपर मैनेजमेंट और मैपिंग रूल्स का UI लोड होगा
        render_shipper_data()

if __name__ == "__main__":
    main()
