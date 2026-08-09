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
                    "igst_config": {"lut_keywords": "", "paid_keywords": ""}
                }
            
            shipper_info = st.session_state["shipper_database"][s_name]
            
            if isinstance(s_data, dict):
                shipper_info["mapping_rules"] = s_data.get("mapping_rules", {})
                shipper_info["item_table_rules"] = s_data.get("item_table_rules", {})
                shipper_info["item_table_rule_name"] = s_data.get("item_table_rule_name", "parser_sample")
                shipper_info["target_sheet_link"] = s_data.get("target_sheet_link", "")
                shipper_info["target_tab_name"] = s_data.get("target_tab_name", "Sheet1")
                shipper_info["igst_config"] = s_data.get("igst_config", {"lut_keywords": "", "paid_keywords": ""})

        if show_toast: st.toast("✅ GitHub से सभी रूल्स लोड हो गए!")
    except Exception as e:
        if show_toast: st.error(f"फ़ैच एरर: {str(e)}")

@st.dialog("🧪 Live Extraction Field Test Result")
def show_field_test_dialog(field_name, rule_data, result_val):
    st.write(f"### 🔍 Field: **`{field_name}`**")
    st.markdown("#### 📋 Applied Rule Parameters:")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"* **Keyword:** `{rule_data.get('keyword', 'N/A')}`")
        st.markdown(f"* **Position:** `{rule_data.get('position', 'Right (आगे)')}`")
    with col_b:
        st.markdown(f"* **Match Mode:** `{rule_data.get('match_mode', 'Exact Word')}`")
        st.markdown(f"* **Filter/Logic:** `{rule_data.get('filter', 'None')}`")
        
    st.write("---")
    st.markdown("#### 🎯 Extracted Result from Uploaded File:")
    if "❌" in result_val or not result_val.strip():
        st.error(f"❌ **Not Found!** Value: `{result_val}`")
    else:
        st.success("🎉 **SUCCESS! Extracted Value:**")
        st.code(result_val, language="text")

@st.dialog("➕ Add New Custom Header Field")
def add_custom_header_field_dialog(selected_shipper):
    st.write("यहाँ नया हेडर फ़ील्ड जोड़ें:")
    new_field = st.text_input("Field Name (उदा: Invoice No, GST Inv No):")
    
    if st.button("Confirm & Add Field", type="primary"):
        if not new_field.strip():
            st.error("फ़ील्ड नाम खाली नहीं हो सकता!")
        else:
            rules = st.session_state["shipper_database"][selected_shipper].setdefault("mapping_rules", {})
            rules[new_field.strip()] = {
                "keyword": "", "position": "Right (आगे)", "cell": "",
                "match_mode": "Exact Word", "stop_kw": "", "filter": "None", "fallback": ""
            }
            st.success(f"🎉 फ़ील्ड '{new_field}' जुड़ गया!")
            st.rerun()

@st.dialog("➕ Add Item Column Rule")
def add_item_col_dialog(selected_shipper):
    st.write("यहाँ आइटम टेबल के लिए नया कॉलम हेडिंग और एक्सेल कॉलम जोड़ें:")
    c_name = st.text_input("Heading Name (उदा: Net Weight, Boxes, Size):")
    c_col = st.text_input("Excel Column Letter (उदा: L, M, N, Z):").upper()
    c_type = st.selectbox("Rule Type:", ["PDF Row Item", "Constant Text", "Smart Detection"])
    c_rule = st.text_input("Rule Detail / Value (उदा: B19, SET, PCS):")
    
    if st.button("Confirm & Add Item Column", type="primary"):
        if not c_name or not c_col:
            st.error("Heading Name और Column Letter अनिवार्य हैं!")
        else:
            item_rules = st.session_state["shipper_database"][selected_shipper].setdefault("item_table_rules", {})
            item_rules[c_name] = {"col": c_col, "type": c_type, "rule": c_rule}
            st.success(f"🎉 कॉलम '{c_name}' जुड़ गया!")
            st.rerun()

def render_shipper_data():
    if "github_data_loaded" not in st.session_state:
        fetch_data_from_github(show_toast=False)
        st.session_state["github_data_loaded"] = True
    
    st.header("🏢 Shipper Management & GitHub Rules Sync")
    st.caption("सटीक डेटा एक्सट्रैक्शन और GitHub JSON आधारित रूल्स कॉन्फ़िगरेशन।")
    
    with st.expander("➕ Add New Shipper (नया शिपर जोड़ें)", expanded=False):
        new_shipper_name = st.text_input("नया शिपर कंपनी का नाम दर्ज करें:", key="input_new_shipper_name")
        
        if st.button("Create New Shipper Profile", type="primary", key="btn_create_shipper"):
            if not new_shipper_name.strip():
                st.error("शिपर का नाम खाली नहीं हो सकता!")
            else:
                s_clean = new_shipper_name.strip()
                if s_clean not in st.session_state["shipper_database"]:
                    st.session_state["shipper_database"][s_clean] = {
                        "mapping_rules": {},
                        "item_table_rules": {},
                        "item_table_rule_name": "parser_sample",
                        "target_sheet_link": "",
                        "target_tab_name": "Sheet1",
                        "igst_config": {"lut_keywords": "", "paid_keywords": ""}
                    }
                    st.success(f"🎉 नया शिपर '{s_clean}' सफलतापूर्वक जुड़ गया है!")
                    st.rerun()
                else:
                    st.warning("⚠️ यह शिपर पहले से मौजूद है!")

    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if shippers_list:
        # डिफ़ॉल्ट रूप से खाली / None ताकि कोई शिपर पहले से सेलेक्टेड न रहे
        selected_shipper = st.selectbox(
            "कॉन्फ़िगर करने के लिए शिपर चुनें:", 
            options=["-- कृपया शिपर चुनें या सर्च करें --"] + shippers_list, 
            index=0,
            key="admin_shipper_select"
        )
        
        if selected_shipper != "-- कृपया शिपर चुनें या सर्च करें --":
            st.write(f"### ⚙️ प्रोफाइल सेटअप और रूल्स: **{selected_shipper}**")
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            # 1. डायनामिक पार्सर सिलेक्शन ड्रॉपडाउन
            available_parsers = ["parser_sample"]
            current_parser = shipper_info.get("item_table_rule_name", "parser_sample")
            if current_parser not in available_parsers:
                available_parsers.append(current_parser)
                
            p_idx = available_parsers.index(current_parser) if current_parser in available_parsers else 0
            
            updated_parser_choice = st.selectbox(
                "📌 इस शिपर के लिए एक्टिव पार्सर रूल (Parser File) चुनें:", 
                available_parsers, 
                index=p_idx, 
                key=f"sel_parser_{selected_shipper}"
            )
            shipper_info["item_table_rule_name"] = updated_parser_choice

            # 2. Target Google Sheet Link और Sheet/Tab Name इनपुट फील्ड्स
            st.markdown("#### ☁️ Target Google Sheet Destination Config")
            col_gs1, col_gs2 = st.columns(2)
            with col_gs1:
                target_sheet_link = st.text_input(
                    "Target Google Sheet Link / ID:",
                    value=shipper_info.get("target_sheet_link", ""),
                    key=f"target_sheet_link_{selected_shipper}",
                    placeholder="यहाँ गूगल शीट की लिंक या ID दर्ज करें"
                )
            with col_gs2:
                target_tab_name = st.text_input(
                    "Target Tab / Sheet Name:",
                    value=shipper_info.get("target_tab_name", "Sheet1"),
                    key=f"target_tab_name_{selected_shipper}",
                    placeholder="उदा: INV या Sheet1"
                )
            
            shipper_info["target_sheet_link"] = target_sheet_link
            shipper_info["target_tab_name"] = target_tab_name

            st.write("---")
            st.subheader("🧪 Instant PDF Upload & Live Data Test Engine")
            
            test_pdf = st.file_uploader("➡️ टेस्ट करने के लिए इनवॉइस PDF अपलोड करें", type=["pdf"], key=f"test_pdf_{selected_shipper}")
            
            pdf_lines = []
            pdf_text = ""
            if test_pdf:
                st.session_state["cached_pdf_bytes"] = test_pdf.getvalue()
                with pdfplumber.open(test_pdf) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            pdf_text += t + "\n"
                            pdf_lines.extend(t.split("\n"))
                st.session_state["cached_pdf_lines"] = pdf_lines
                st.session_state["cached_pdf_text"] = pdf_text
                st.success(f"📄 PDF अपलोड है ({len(pdf_lines)} पंक्तियाँ)। अब नीचे ⚡ Test बटन दबाएँ!")

            st.write("---")
            
            col_title, col_sync = st.columns([6, 4])
            with col_title:
                st.subheader("🛠️ Header Fields Mapping Rules")
            with col_sync:
                if st.button("🔄 Reload from GitHub", type="secondary", use_container_width=True):
                    with st.spinner("⏳ GitHub से रूल्स लोड हो रहे हैं..."):
                        fetch_cached_github_data.clear()
                        st.session_state["github_data_loaded"] = False
                        st.session_state["shipper_database"] = {}
                        fetch_data_from_github(show_toast=True)
                    st.rerun()

            if st.button("➕ Add Header Field", key="btn_add_h_field"):
                add_custom_header_field_dialog(selected_shipper)
            
            current_rules = shipper_info.get("mapping_rules", {})
            updated_rules = {}
            
            pos_options = ["Right (आगे)", "Below (नीचे)", "2 Lines Below", "📦 Extract Inside Box (डब्बे के अंदर का टेक्स्ट)"]
            mode_options = ["Exact Word", "Word Position", "Full Line", "After Word"]
            filter_options = ["None", "Text Inside Parentheses ()", "Numbers Only", "Clean Date (DD/MM/YYYY)"]
            
            for field in list(current_rules.keys()):
                s_val = current_rules[field]
                c1, c2, c3, c4, c5, c10, c11 = st.columns([2.0, 2.5, 1.5, 1.5, 1.5, 0.6, 0.9])
                
                with c1: edited_name = st.text_input(f"f_{field}", value=field, label_visibility="collapsed")
                with c2: ky = st.text_input(f"k_{field}", value=s_val.get("keyword", ""), label_visibility="collapsed")
                with c3: pos = st.selectbox(f"p_{field}", pos_options, index=0, label_visibility="collapsed")
                with c4: m_mode = st.selectbox(f"mm_{field}", mode_options, index=0, label_visibility="collapsed")
                with c5: final_flt = st.selectbox(f"flt_{field}", filter_options, index=0, label_visibility="collapsed")
                with c10:
                    if st.button("🗑️", key=f"del_h_{field}"):
                        del st.session_state["shipper_database"][selected_shipper]["mapping_rules"][field]
                        st.rerun()
                with c11:
                    if st.button("⚡ Test", key=f"test_btn_{field}"):
                        curr_pdf_lines = st.session_state.get("cached_pdf_lines", [])
                        curr_pdf_text = st.session_state.get("cached_pdf_text", "")
                        if not curr_pdf_lines:
                            st.toast("⚠️ पहले ऊपर PDF अपलोड करें!")
                        else:
                            pdf_bytes = st.session_state.get("cached_pdf_bytes", None)
                            res_val = extract_header_value(curr_pdf_lines, curr_pdf_text, ky, pos, m_mode, "", final_flt, field_label=edited_name, pdf_bytes=pdf_bytes)
                            show_field_test_dialog(edited_name, {"keyword": ky, "position": pos, "match_mode": m_mode, "filter": final_flt}, res_val if res_val else "❌ (Not Found)")
                
                updated_rules[edited_name] = {"keyword": ky, "position": pos, "match_mode": m_mode, "filter": final_flt}
                
            shipper_info["mapping_rules"] = updated_rules

            st.write("---")
            c_head, c_add_btn = st.columns([7, 3])
            with c_head:
                st.subheader("📦 Dynamic Item Table Column Builder")
            with c_add_btn:
                if st.button("➕ Add Item Column", use_container_width=True, key="btn_add_item_col_main"):
                    add_item_col_dialog(selected_shipper)
            
            item_rules = shipper_info.get("item_table_rules", {})
            updated_item_rules = {}
            
            for item_field in list(item_rules.keys()):
                ir = item_rules[item_field]
                ic1, ic2, ic3, ic4, ic6 = st.columns([3.0, 1.5, 3.0, 3.0, 0.8])
                
                with ic1: e_ifield = st.text_input(f"if_{item_field}", value=item_field, label_visibility="collapsed")
                with ic2: e_icol = st.text_input(f"ic_{item_field}", value=ir.get("col", "K"), label_visibility="collapsed").upper()
                with ic3: e_itype = st.selectbox(f"it_{item_field}", ["PDF Row Item", "Constant Text", "Smart Detection"], index=0, label_visibility="collapsed")
                with ic4: e_irule = st.text_input(f"ir_{item_field}", value=ir.get("rule", ""), label_visibility="collapsed")
                with ic6:
                    if st.button("🗑️", key=f"idel_{item_field}"):
                        del item_rules[item_field]
                        st.rerun()
                        
                updated_item_rules[e_ifield] = {"col": e_icol, "type": e_itype, "rule": e_irule}
                
            shipper_info["item_table_rules"] = updated_item_rules
            st.write("---")
            
            # 🚀 GitHub पर रूल्स सेव करने का बटन (Google Sheet लिंक और टैब नेम सहित)
            if st.button("💾 Save Rules to GitHub JSON", type="primary", use_container_width=True, key="btn_save_rules_github"):
                shippers_payload = {}
                for s_name, s_data in st.session_state["shipper_database"].items():
                    shippers_payload[s_name] = {
                        "mapping_rules": s_data.get("mapping_rules", {}),
                        "item_table_rules": s_data.get("item_table_rules", {}),
                        "item_table_rule_name": s_data.get("item_table_rule_name", "parser_sample"),
                        "target_sheet_link": s_data.get("target_sheet_link", ""),
                        "target_tab_name": s_data.get("target_tab_name", "Sheet1"),
                        "igst_config": s_data.get("igst_config", {})
                    }
                
                with st.spinner("⏳ GitHub JSON पर रूल्स सेव हो रहे हैं..."):
                    success = push_rules_to_github(shippers_payload)
                    if success:
                        fetch_cached_github_data.clear()
                        st.session_state["github_data_loaded"] = False
                        st.success("🎉 सफलता! आपके सारे रूल्स GitHub पर सुरक्षित सेव हो गए हैं!")
                        st.balloons()
                    else:
                        st.error("❌ GitHub पर रूल्स सेव करते समय एरर आया! कृपया GitHub Token / API चेक करें।")
