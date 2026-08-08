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
        rules = st.session_state["shipper_database"][selected_shipper].setdefault("mapping_rules", {})
        rules[new_field.strip()] = {"keyword": "", "position": "Right (आगे)", "match_mode": "Exact Word", "filter": "None"}
        st.rerun()

@st.dialog("➕ Add Item Column Rule")
def add_item_col_dialog(selected_shipper):
    c_name = st.text_input("Heading Name (उदा: Net Weight):")
    c_col = st.text_input("Excel Column (उदा: L):").upper()
    if st.button("Save"):
        item_rules = st.session_state["shipper_database"][selected_shipper].setdefault("item_table_rules", {})
        item_rules[c_name] = {"col": c_col, "type": "PDF Row Item", "rule": ""}
        st.rerun()

@st.dialog("➕ Add Excel Header")
def add_excel_header_dialog(selected_shipper):
    h_name = st.text_input("Header Name (उदा: Total Amount):")
    h_col = st.text_input("Excel Column (उदा: C):").upper()
    if st.button("Save"):
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

        # 3. Excel Download Header Configuration (Exact 8-Column Visible + Single Bottom Scrollbar)
        st.write("---")
        c_eh_head, c_eh_btn = st.columns([7, 3])
        with c_eh_head:
            st.subheader("📊 Excel Download Header Configuration")
            st.caption("एक बार में 8 कॉलम दिखेंगे, बाकी देखने के लिए नीचे दिए गए स्क्रॉल बार का उपयोग करें:")
        with c_eh_btn:
            if st.button("➕ Add Header", use_container_width=True):
                add_excel_header_dialog(selected_shipper)
        
        if "excel_headers" not in shipper_info:
            shipper_info["excel_headers"] = {"Invoice No": "A", "Date": "B"}
            
        updated_excel_headers = {}
        header_items = list(shipper_info["excel_headers"].items())
        
        # 🚀 परफेक्ट CSS: एक बार में ठीक 8 कॉलम दिखेंगे (8 * 160px = 1280px), और नीचे सिंगल स्क्रॉल बार आएगा
        st.markdown("""
        <style>
        /* मास्टर स्क्रॉल कंटेनर जिसकी चौड़ाई बिल्कुल 8 कॉलम के बराबर फिक्स है */
        .excel-eight-col-container {
            display: flex;
            flex-direction: row;
            overflow-x: auto;
            gap: 12px;
            padding: 10px 5px 20px 5px;
            width: 100%;
            max-width: 1320px; /* ठीक 8 कॉलम के लायक स्पेस */
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #ced4da;
            white-space: nowrap;
        }
        /* हर एक कॉलम की फिक्स और बढ़िया चौड़ाई */
        .excel-col-card-item {
            flex: 0 0 150px !important;
            min-width: 150px !important;
            max-width: 150px !important;
            background: #ffffff !important;
            border: 1px solid #dee2e6 !important;
            border-radius: 6px !important;
            padding: 10px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
            vertical-align: top !important;
            white-space: normal !important;
        }
        /* सबसे नीचे दिखने वाली साफ़ और सुंदर स्क्रॉल बार */
        .excel-eight-col-container::-webkit-scrollbar {
            height: 12px;
        }
        .excel-eight-col-container::-webkit-scrollbar-thumb {
            background: #adb5bd;
            border-radius: 6px;
        }
        .excel-eight-col-container::-webkit-scrollbar-track {
            background: #e9ecef;
            border-radius: 6px;
        }
        </style>
        """, unsafe_allow_html=True)

        if header_items:
            # आउटर स्क्रॉल कंटेनर शुरू
            st.markdown('<div class="excel-eight-col-container">', unsafe_allow_html=True)
            
            # कॉलम रेंडर करने के लिए लूप
            cols = st.columns(len(header_items))
            for idx, (h_name, h_col) in enumerate(header_items):
                with cols[idx]:
                    st.markdown('<div class="excel-col-card-item">', unsafe_allow_html=True)
                    
                    e_hname = st.text_input("H", value=h_name, key=f"col8_h_{idx}", label_visibility="collapsed")
                    
                    sub_c1, sub_c2 = st.columns([2.5, 1])
                    with sub_c1:
                        e_hcol = st.text_input("C", value=h_col, key=f"col8_c_{idx}", label_visibility="collapsed").upper()
                    with sub_c2:
                        if st.button("🗑️", key=f"col8_del_{idx}"):
                            del shipper_info["excel_headers"][h_name]
                            st.rerun()
                            
                    st.markdown('</div>', unsafe_allow_html=True)
                    updated_excel_headers[e_hname] = e_hcol
                    
            st.markdown('</div>', unsafe_allow_html=True)
            
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
