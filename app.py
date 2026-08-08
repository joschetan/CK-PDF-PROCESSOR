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

# Session States Initialize करें
if "app_authenticated" not in st.session_state:
    st.session_state.app_authenticated = False

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# 1. सामान्य यूजर लॉगिन (App View)
def check_app_password():
    def app_pass_entered():
        # 🔑 यहाँ सामान्य यूजर/ऑपरेटर का पासवर्ड सेट करें
        if st.session_state["app_pass_input"] == "ck_user_2026":
            st.session_state.app_authenticated = True
            del st.session_state["app_pass_input"]
        else:
            st.session_state.app_authenticated = False
            st.error("😕 गलत पासवर्ड! कृपया सही ऑपरेटर पासवर्ड दर्ज करें।")

    if not st.session_state.app_authenticated:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("## 📄 CK PDF PROCESSOR - LOGIN")
            st.markdown("इनवॉइस प्रोसेसिंग ज़ोन में प्रवेश करने के लिए पासवर्ड दर्ज करें:")
            st.text_input(
                "Enter App Password", 
                type="password", 
                on_change=app_pass_entered, 
                key="app_pass_input"
            )
        return False
    return True

# 2. एडमिन लॉगिन (Shipper & Rules Configuration)
def check_admin_password():
    st.markdown("---")
    st.subheader("🔐 Admin Configuration Zone")
    
    if not st.session_state.admin_authenticated:
        st.info("⚠️ शिपर जोड़ने या मैपिंग रूल्स बदलने के लिए एडमिन पासवर्ड आवश्यक है।")
        
        def admin_pass_entered():
            # 🔑 यहाँ सुरक्षित एडमिन पासवर्ड सेट करें
            if st.session_state["admin_pass_input"] == "ck_admin_2026":
                st.session_state.admin_authenticated = True
                del st.session_state["admin_pass_input"]
                st.success("🎉 एडमिन एक्सेस मिल गया है!")
                st.rerun()
            else:
                st.session_state.admin_authenticated = False
                st.error("😕 गलत एडमिन पासवर्ड!")

        st.text_input(
            "Enter Admin Password", 
            type="password", 
            on_change=admin_pass_entered, 
            key="admin_pass_input"
        )
    else:
        col_a, col_b = st.columns([8, 2])
        with col_a:
            st.success("🔓 Admin Mode Active (आप एडमिन के रूप में लॉग इन हैं)")
        with col_b:
            if st.button("🔒 Lock Admin Zone", use_container_width=True):
                st.session_state.admin_authenticated = False
                st.rerun()
                
        # एडमिन पैनल लोड होगा
        render_shipper_data()

def main():
    # सबसे पहले ऐप का जनरल पासवर्ड चेक होगा
    if not check_app_password():
        return

    st.title("📄 CK PDF PROCESSOR")
    st.markdown("---")

    # 1. Main Processing Zone (सबके लिए उपलब्ध जो ऐप पासवर्ड से अंदर हैं)
    render_processor()

    # 2. नीचे एडमिन कॉन्फ़िगरेशन ज़ोन (अलग एडमिन पासवर्ड से सुरक्षित)
    check_admin_password()
    
    # ऐप से पूरी तरह बाहर आने (Logout) के लिए बटन
    st.markdown("<br><hr>", unsafe_allow_html=True)
    if st.button("🚪 Logout Complete App"):
        st.session_state.app_authenticated = False
        st.session_state.admin_authenticated = False
        st.rerun()

if __name__ == "__main__":
    main()
