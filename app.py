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
if "app_authenticated" not in st.session_state:
    st.session_state.app_authenticated = False

def check_app_password():
    """Returns True if the user entered the correct global app password."""
    def password_entered():
        # आप यहाँ अपना मनचाहा पासवर्ड सेट कर सकते हैं (वर्तमान में: ck_admin_2026)
        if st.session_state["global_password_input"] == "CK":
            st.session_state.app_authenticated = True
            del st.session_state["global_password_input"]
        else:
            st.session_state.app_authenticated = False
            st.error("😕 गलत पासवर्ड! कृपया सही पासवर्ड दर्ज करें।")

    if not st.session_state.app_authenticated:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("## 🔐 CK PDF PROCESSOR - LOGIN")
            st.markdown("यह एक सुरक्षित एप्लिकेशन है। आगे बढ़ने के लिए कृपया एडमिन पासवर्ड दर्ज करें।")
            st.text_input(
                "Enter Application Password", 
                type="password", 
                on_change=password_entered, 
                key="global_password_input"
            )
        return False
    return True

def main():
    # 🚀 सबसे पहले ग्लोबल पासवर्ड चेक होगा
    if not check_app_password():
        return

    # यदि पासवर्ड सही है, तो ऐप का मुख्य इंटरफेस दिखेगा
    st.title("📄 CK PDF PROCESSOR")
    st.markdown("---")

    # 1. Main Processing Zone (SS1)
    render_processor()

    st.markdown("---")
    
    # 2. Main Page के बिल्कुल नीचे Shipper Management & Mapping Rules Zone
    st.subheader("⚙️ Shipper Management & Mapping Rules")
    
    with st.expander("🛠️ Open Shipper Configuration Panel (Click to Expand)", expanded=False):
        render_shipper_data()
        
    # नीचे लॉगआउट बटन ताकि कोई भी यूजर काम करने के बाद सेशन सुरक्षित बंद कर सके
    st.markdown("<br><hr>", unsafe_allow_html=True)
    if st.button("🔒 Lock / Logout App"):
        st.session_state.app_authenticated = False
        st.rerun()

if __name__ == "__main__":
    main()
