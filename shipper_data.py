import streamlit as st
import pdfplumber
import re
from io import BytesIO

from pdf_engine import extract_header_value
from github_sync import fetch_rules_from_github, push_rules_to_github

def ensure_default_shipper():
    if "shipper_database" not in st.session_state:
        st.session_state["shipper_database"] = {}
        
    s_name = "WELSPUN GLOBAL BRANDS LIMITED"
    if s_name not in st.session_state["shipper_database"]:
        st.session_state["shipper_database"][s_name] = {
            "mapping_rules": {},
            "item_table_rules": {},
            "item_table_rule_name": "parser_sample",
            "target_sheet_link": "",
            "target_tab_name": "Sheet1",
            "excel_headers": {"Invoice No": "A", "Date": "B"},
            "igst_config": {"lut_keywords": "", "paid_keywords": ""}
        }

@st.cache_data(show_spinner=False)
def fetch_cached_github_data():
    return fetch_rules_from_github()

def fetch_data_from_github(show_toast=False):
    ensure_default_shipper()
    try:
        data = fetch_cached_github_data()
        if not data:
            if show_toast: st.error("⚠️ GitHub से रूल्स डेटा नहीं मिला.")
            return

        shippers_dict = data.get("shippers", {})
        if not shippers_dict and isinstance(data, dict):
            shippers_dict = data
        
        for s_name, s_data in shippers_dict.items():
            if not s_name or s_name == "error":
                continue
                
            if s_name not in st.session_state["shipper_database"]:
                st.session_state["shipper_database"][s_name] = {
                    "mapping_rules": {},
                    "item_table_rules": {},
                    "item_table_rule_name": "parser_sample",
                    "target_sheet_link": "",
                    "target_tab_name": "Sheet1",
                    "excel_headers": {"Invoice No": "A", "Date": "B"},
                    "igst_config": {"lut_keywords": "", "paid_keywords": ""}
                }
            
            shipper_info = st.session_state["shipper_database"][s_name]
            
            if isinstance(s_data, dict):
                shipper_info["mapping_rules"] = s_data.get("mapping_rules", {})
                shipper_info["item_table_rules"] = s_data.get("item_table_rules", {})
                shipper_info["item_table_rule_name"] = s_data.get("item_table_rule_name", "parser_sample")
                shipper_info["target_sheet_link"] = s_data.get("target_sheet_link", "")
                shipper_info["target_tab_name"] = s_data.get("target_tab_name", "Sheet1")
                shipper_info["excel_headers"] = s_data.get("excel_headers", {"Invoice No": "A", "Date": "B"})
                shipper_info["igst_config"] = s_data.get("igst_config", {"lut_keywords": "", "paid_keywords": ""})

        if show_toast: st.toast("✅ GitHub से सभी रूल्स लोड हो गए!")
    except Exception as e:
        if show_toast: st.error(f"फ़ैच एरर: {str(e)}")

@st.dialog("🧪 Live Extraction Field Test Result")
def show_field_test_dialog(field_name, rule_data, result_val):
    st.write(f"### 🔍 Field: **`{field_name}`**")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"* **Keyword:** `{rule_data.get('keyword', 'N/A')}`")
        st.markdown(f"* **Position:** `{rule_data.get('position', 'Right (आगे)')}`")
    with col_b:
        st.markdown(f"* **Match Mode:** `{rule_data.get('match_mode', 'Exact Word')}`")
        st.markdown(f"* **Filter/Logic:** `{rule_data.get('filter', 'None')}`")
    st.write("---")
    if "❌" in result_val or not result_val.strip():
        st.error(f"❌ **Not Found!**")
    else:
        st.success("🎉 **SUCCESS! Extracted Value:**")
        st.code(result_val, language="text")

@st.dialog("➕ Add New Custom Header Field")
def add_custom_header_field_dialog(selected_shipper):
    new_field = st.text_input("Field Name (उदा: Invoice No):")
    if st.button("Save"):
        ensure_default_shipper()
        if selected_shipper not in st.session_state["shipper_database"]:
            st.session_state["shipper_database"][selected_shipper] = {}
            
        rules = st.session_state["shipper_database"][selected_shipper].setdefault("mapping_rules", {})
        rules[new_field.strip()] = {"keyword": "", "position": "Right (आगे)", "match_mode": "Exact Word", "filter": "None"}
        st.rerun()

@st.dialog("➕ Add Item Column Rule")
def add_item_col_dialog(selected_shipper):
    c_name = st.text_input("Heading Name (उदा: Net Weight):")
    c_col = st.text_input("Excel Column (उदा: L):").upper()
    if st.button("Save"):
        ensure_default_shipper()
        if selected_shipper not in st.session_state["shipper_database"]:
            st.session_state["shipper_database"][selected_shipper] = {}
            
        item_rules = st.session_state["shipper_database"][selected_shipper].setdefault("item_table_rules", {})
        item_rules[c_name] = {"col": c_col, "type": "PDF Row Item", "rule": ""}
        st.rerun()

@st.dialog("➕ Add Excel Header")
def add_excel_header_dialog(selected_shipper):
    h_name = st.text_input("Header Name (उदा: Total Amount):")
    h_col = st.text_input("Excel Column (उदा: C):").upper()
    if st.button("Save"):
        ensure_default_shipper()
        if selected_shipper not in st.session_state["shipper_database"]:
            st.session_state["shipper_database"][selected_shipper] = {}
            
        headers = st.session_state["shipper_database"][selected_shipper].setdefault("excel_headers", {})
        headers[h_name.strip()] = h_col.strip()
        st.rerun()

def render_shipper_data():
    ensure_default_shipper()
    
    if "github_data_loaded" not in st.session_state:
        fetch_data_from_github(show_toast=False)
        st.session_state["github_data_loaded"] = True
    
    st.header("🏢 Shipper Management")
    shippers_list = list(st.session_state["shipper_database"].keys())
    selected_shipper = st.selectbox("कॉन्फ़िगर करने के लिए शिपर चुनें:", shippers_list)
    
    if selected_shipper:
        shipper_info = st.session_state["shipper_database"][selected_shipper]
        
        # 1. Parser Dropdown
        updated_parser_choice = st.selectbox("📌 एक्टिव पार्सर रूल:", ["parser_sample"], index=0)
        shipper_info["item_table_rule_name"] = updated_parser_choice

        # 2. Sheet Config
        st.markdown("#### ☁️ Target Google Sheet Destination Config")
        col_gs1, col_gs2 = st.columns(2)
        with col_gs1: shipper_info["target_sheet_link"] = st.text_input("Sheet Link / ID:", value=shipper_info.get("target_sheet_link", ""))
        with col_gs2: shipper_info["target_tab_name"] = st.text_input("Tab Name:", value=shipper_info.get("target_tab_name", "Sheet1"))

        # 3. Excel Download Header Configuration (Pure HTML Flex Scrollable Table)
        st.write("---")
        c_eh_head, c_eh_btn = st.columns([7, 3])
        with c_eh_head:
            st.subheader("📊 Excel Download Header Configuration")
            st.caption("एक्सेल जैसा लेआउट: फिक्स चौड़ाई, साफ़ हेडिंग्स और नीचे सिंगल हॉरिजॉन्टल स्क्रॉल बार:")
        with c_eh_btn:
            if st.button("➕ Add Header", use_container_width=True):
                add_excel_header_dialog(selected_shipper)
        
        if "excel_headers" not in shipper_info:
            shipper_info["excel_headers"] = {"Invoice No": "A", "Date": "B"}
            
        updated_excel_headers = {}
        header_items = list(shipper_info["excel_headers"].items())
        
        # 🚀 परफेक्‍ट CSS: Streamlit कॉलम के बखेड़े को खत्म करके शुद्ध HTML Flexbox का उपयोग
        st.markdown("""
        <style>
        .excel-table-scroll-wrapper {
            display: flex;
            flex-direction: row;
            overflow-x: auto;
            gap: 15px;
            padding: 15px 5px 25px 5px;
            width: 100%;
            background-color: #f8f9fa;
            border-radius: 10px;
            border: 1px solid #ced4da;
        }
        .excel-table-scroll-wrapper::-webkit-scrollbar {
            height: 12px;
        }
        .excel-table-scroll-wrapper::-webkit-scrollbar-thumb {
            background: #adb5bd;
            border-radius: 6px;
        }
        .excel-table-scroll-wrapper::-webkit-scrollbar-track {
            background: #e9ecef;
            border-radius: 6px;
        }
        .excel-header-card {
            flex: 0 0 175px;
            min-width: 175px;
            max-width: 175px;
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        </style>
        """, unsafe_allow_html=True)

        # हम Streamlit के फॉर्म या इनपुट को बिना st.columns के सीधे जनरेट करेंगे ताकि पिचकें नहीं
        # चूंकि st.text_input को यूनिक की चाहिए, हम HTML फॉर्म के अंदर Streamlit widgets को लूप करेंगे
        
        # इसके लिए आउटर डिव शुरू
        st.markdown('<div class="excel-table-scroll-wrapper">', unsafe_allow_html=True)
        
        # HTML कंटेनर के भीतर Streamlit कॉम्पोनेंट्स को सही से दिखाने के लिए हम एक छोटी सी ट्रिक का उपयोग करेंगे
        # चूंकि HTML के अंदर सीधे Streamlit विजेट्स रेंडर नहीं होते, हम हर कार्ड को एक छोटे कॉलम ब्लॉक में रखेंगे 
        # और CSS से उनकी चौड़ाई एकदम सख्त फिक्स कर देंगे।
        
        if header_items:
            # यहाँ हम कॉलम की संख्या के बराबर कॉलम बनाएंगे, लेकिन CSS उन्हें फैलने नहीं देगी बल्कि स्क्रॉल लाएगी
            cols = st.columns(len(header_items))
            for idx, (h_name, h_col) in enumerate(header_items):
                with cols[idx]:
                    # हर कार्ड को फिक्स विड्थ देने के लिए इनलाइन स्टाइल और क्लास
                    st.markdown('<div style="width: 175px; min-width: 175px; background: #ffffff; padding: 10px; border: 1px solid #dee2e6; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">', unsafe_allow_html=True)
                    
                    e_hname = st.text_input("H", value=h_name, key=f"perfect_eh_{idx}", label_visibility="collapsed")
                    
                    sc1, sc2 = st.columns([2.5, 1])
                    with sc1:
                        e_hcol = st.text_input("C", value=h_col, key=f"perfect_ec_{idx}", label_visibility="collapsed").upper()
                    with sc2:
                        if st.button("🗑️", key=f"perfect_del_{idx}"):
                            del shipper_info["excel_headers"][h_name]
                            st.rerun()
                            
                    st.markdown('</div>', unsafe_allow_html=True)
                    updated_excel_headers[e_hname] = e_hcol
                    
        st.markdown('</div>', unsafe_allow_html=True)
        
        # CSS को मजबूर करने के लिए कि वह स्ट्रीमलिट के कॉलम रैपर को स्ट्रेच न होने दे
        st.markdown("""
        <style>
        div[data-testid="column"] {
            width: 175px !important;
            flex: 0 0 175px !important;
            min-width: 175px !important;
            max-width: 175px !important;
            display: inline-block !important;
        }
        </style>
        """, unsafe_allow_html=True)

        shipper_info["excel_headers"] = updated_excel_headers

        # 4. Save Button
        st.write("---")
        if st.button("💾 Save Rules to GitHub JSON", type="primary", use_container_width=True):
            shippers_payload = {}
            for s_name, s_data in st.session_state["shipper_database"].items():
                shippers_payload[s_name] = {
                    "mapping_rules": s_data.get("mapping_rules", {}),
                    "item_table_rules": s_data.get("item_table_rules", {}),
                    "item_table_rule_name": s_data.get("item_table_rule_name", "parser_sample"),
                    "target_sheet_link": s_data.get("target_sheet_link", ""),
                    "target_tab_name": s_data.get("target_tab_name", "Sheet1"),
                    "excel_headers": s_data.get("excel_headers", {})
                }
            if push_rules_to_github(shippers_payload):
                st.success("🎉 सफलता! रूल्स GitHub पर सुरक्षित हैं।")
            else:
                st.error("❌ GitHub एरर!")
