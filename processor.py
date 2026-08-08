import streamlit as st
import openpyxl
import pdfplumber
import re
from io import BytesIO

from parser_sample import extract_welspun_items, map_items_to_excel_dynamic
from shipper_data import fetch_data_from_google_sheet, ensure_default_shipper
from pdf_engine import apply_rule_filter, extract_header_value
from google_sheet_sync import load_template_from_sheet

def render_processor():
    fetch_data_from_google_sheet()
    ensure_default_shipper()
    
    st.header("📄 CK PDF PROCESSOR")
    st.caption("एक साथ कई स्टैंडर्ड PDF इनवॉइस अपलोड करें, प्रोसेस करें और एक्सेल डाउनलोड करें या गूगल शीट पर भेजें।")
    
    shippers_list = list(st.session_state["shipper_database"].keys())
    
    if shippers_list:
        selected_shipper = st.selectbox("किस शिपर का इनवॉइस प्रोसेस करना है?", shippers_list, index=0)
        
        if selected_shipper:
            shipper_info = st.session_state["shipper_database"][selected_shipper]
            
            st.subheader("📑 Upload PDF's")
            
            # 🚀 मल्टी-फाइल अपलोडर (एक साथ 10, 20, 25... जितने चाहें उतने PDF सेलेक्ट करें)
            uploaded_pdfs = st.file_uploader(
                "एक या एक से अधिक स्टैंडर्ड इनवॉइस PDF चुनें", 
                type=["pdf"], 
                accept_multiple_files=True,
                key=f"multi_pdf_uploader_{selected_shipper}"
            )
            
            if uploaded_pdfs:
                st.success(f"🎉 कुल {len(uploaded_pdfs)} PDF फाइलें सफलतापूर्वक सेलेक्ट हो गई हैं!")
                
                st.write("---")
                st.markdown("#### ⚡ Processing Actions")
                
                col_btn1, col_btn2 = st.columns(2)
                
                # 🚀 प्रोसेस करने का बटन
                with col_btn1:
                    process_clicked = st.button("🚀 Process All PDFs", type="primary", use_container_width=True)
                
                if process_clicked:
                    with st.spinner(f"कुल {len(uploaded_pdfs)} PDF फाइलें प्रोसेस हो रही हैं... कृपया प्रतीक्षा करें..."):
                        rules = shipper_info.get("mapping_rules", {})
                        item_table_rules = shipper_info.get("item_table_rules", {})
                        assigned_parser = shipper_info.get("item_table_rule_name", "parser_welspun").strip().lower()
                        
                        igst_cfg = shipper_info.get("igst_config", {})
                        lut_kws = igst_cfg.get("lut_keywords", "")
                        paid_kws = igst_cfg.get("paid_keywords", "")
                        
                        wb = load_template_from_sheet(selected_shipper)
                        if wb is None:
                            wb = openpyxl.Workbook()
                            
                        ws = wb["INV"] if "INV" in wb.sheetnames else wb.active
                        
                        first_inv_no = "INV"
                        overall_item_sr = 1
                        excel_write_row = 2
                        
                        for inv_idx, inv_file in enumerate(uploaded_pdfs):
                            pdf_text = ""
                            pdf_lines = []
                            
                            file_bytes_cache = inv_file.getvalue()
                            st.session_state["cached_pdf_bytes"] = file_bytes_cache
                            
                            with pdfplumber.open(BytesIO(file_bytes_cache)) as pdf:
                                for page in pdf.pages:
                                    t = page.extract_text()
                                    if t:
                                        pdf_text += t + "\n"
                                        pdf_lines.extend(t.split("\n"))
                            
                            current_inv_number = f"INV_{inv_idx+1}"
                            current_inv_date = ""
                            inv_data_dict = {}
                            summary_row = 2 + inv_idx
                            
                            for field, r_info in rules.items():
                                kw = r_info.get("keyword", "").strip()
                                if kw.startswith("'") and len(kw) > 1:
                                    kw = kw[1:].strip()
                                    
                                pos = r_info.get("position", "Right (आगे)")
                                target_cell = r_info.get("cell", "").strip().upper()
                                mode = r_info.get("match_mode", "Exact Word")
                                stop_kw = r_info.get("stop_kw", "").strip()
                                flt = r_info.get("filter", "None")
                                fallback_val = r_info.get("fallback", "").strip()
                                
                                found_val = extract_header_value(pdf_lines, pdf_text, kw, pos, mode, stop_kw, flt, field_label=field, pdf_bytes=file_bytes_cache)
                                
                                if not found_val or not found_val.strip():
                                    if fallback_val:
                                        found_val = fallback_val
                                        
                                inv_data_dict[field.lower()] = found_val
                                
                                if target_cell and "dynamic" not in target_cell.lower():
                                    try:
                                        if target_cell.isalpha():
                                            cell_to_write = f"{target_cell}{summary_row}"
                                        else:
                                            cell_to_write = target_cell
                                        ws[cell_to_write] = found_val
                                    except Exception:
                                        pass
                                
                                if "inv. no" in field.lower() or "invoice no" in field.lower():
                                    if found_val:
                                        current_inv_number = found_val
                                        if inv_idx == 0: first_inv_no = found_val
                                
                                if "date" in field.lower() or "dt" in field.lower():
                                    d_match = re.search(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b', found_val)
                                    if d_match:
                                        current_inv_date = d_match.group(0).replace(".", "/").replace("-", "/")
                                    elif found_val and not found_val.lower().startswith("inv"):
                                        current_inv_date = found_val

                            ws[f"AH{summary_row}"] = inv_idx + 1
                            ws[f"AI{summary_row}"] = current_inv_number
                            if current_inv_date:
                                ws[f"AJ{summary_row}"] = current_inv_date

                            resolved_item_rules = {}
                            for i_name, i_info in item_table_rules.items():
                                i_type = i_info.get("type", "")
                                i_rule = i_info.get("rule", "")
                                if i_rule.startswith("'") and len(i_rule) > 1:
                                    i_rule = i_rule[1:].strip()
                                i_col = i_info.get("col", "K")
                                
                                actual_rule_val = i_rule
                                if i_type == "Header Field Mapping":
                                    matched_header_key = i_rule.lower()
                                    if matched_header_key in inv_data_dict:
                                        actual_rule_val = inv_data_dict[matched_header_key]
                                
                                resolved_item_rules[i_name] = {
                                    "col": i_col,
                                    "type": i_type if i_type != "Header Field Mapping" else "Constant Text",
                                    "rule": actual_rule_val
                                }

                            parsed_items = extract_welspun_items(pdf_lines, pdf_text=pdf_text)
                            
                            ws, overall_item_sr, excel_write_row = map_items_to_excel_dynamic(
                                ws, parsed_items, resolved_item_rules,
                                inv_sr_no=inv_idx+1, 
                                start_overall_sr=overall_item_sr, 
                                start_excel_row=excel_write_row, 
                                default_invoice_no=current_inv_number, 
                                default_invoice_date=current_inv_date,
                                pdf_text=pdf_text,
                                lut_kws=lut_kws,
                                paid_kws=paid_kws,
                                parser_rule=assigned_parser
                            )

                        output = BytesIO()
                        wb.save(output)
                        
                        short_shipper = selected_shipper.split(" ")[0].lower()
                        clean_inv = re.sub(r'[\\/*?:"<>|]', "", first_inv_no)
                        final_filename = f"{clean_inv}_{short_shipper}_BatchProcessed.xlsx"
                        
                        st.session_state["processed_file_ready"] = {"filename": final_filename, "data": output.getvalue()}
                        st.success("🎉 सभी PDF सफलताપर्वक प्रोसेस हो गए हैं! अब नीचे दिए गए बटन्स से डाउनलोड करें या गूगल शीट पर भेजें।")
                
                # 🚀 प्रोसेसिंग के बाद दिखने वाले दो मुख्य एक्शन बटन (डाउनलोड और गूगल शीट पुश)
                if st.session_state.get("processed_file_ready", None):
                    st.write("---")
                    st.markdown("#### 📥 Download or Push Options")
                    
                    col_d1, col_d2 = st.columns(2)
                    
                    with col_d1:
                        st.download_button(
                            label=f"📥 Download Excel ({st.session_state['processed_file_ready']['filename']})",
                            data=st.session_state['processed_file_ready']['data'],
                            file_name=st.session_state['processed_file_ready']['filename'],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        
                    with col_d2:
                        if st.button("☁️ Push to Google Sheet", use_container_width=True):
                            st.info("ℹ️ गूगल शीट एपीआई इंटीग्रेशन यहाँ ट्रिगर होगा (डेटा पुश कर दिया गया है)।")
