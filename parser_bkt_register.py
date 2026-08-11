import re
import pdfplumber
from pdf_engine import apply_rule_filter

def extract_bkt_items(pdf_lines, pdf_text=""):
    """
    BKT Register के आखिरी पेज की आइटम टेबल से 
    Total Net Weight, Total Gross Weight, Quantity और सभी H S Codes निकालने का पार्सर।
    """
    extracted_items = []
    
    total_qty = ""
    total_gross = ""
    total_net = ""
    hs_codes_list = []
    
    # 1. सभी HS Codes ढूंढना (यूनिक और बिना डुप्लीकेट के)
    hs_matches = re.findall(r'(?:HS\s*CODE[#\d\s:]*|CODE[#\s:]*)(\d{8})', pdf_text, re.IGNORECASE)
    if not hs_matches:
        hs_matches = re.findall(r'\b(40\d{6})\b', pdf_text)
        
    for h in hs_matches:
        if h not in hs_codes_list:
            hs_codes_list.append(h)
            
    combined_hscodes = ", ".join(hs_codes_list) if hs_codes_list else ""

    # 2. टेबल की 'Total' वाली लाइन से Qty, Gross Weight और Net Weight ढूंढना
    for line in pdf_lines:
        clean_line = line.strip()
        if clean_line.lower().startswith("total") or "total" in clean_line.lower():
            numbers_in_line = re.findall(r'\b[\d,]+\.\d{3}\b|\b\d+\b', clean_line)
            if len(numbers_in_line) >= 3:
                decimals = [n for n in numbers_in_line if '.' in n or ',' in n]
                ints = [n for n in numbers_in_line if '.' not in n and ',' not in n]
                
                if ints:
                    total_qty = ints[0]
                if len(decimals) >= 2:
                    total_net = decimals[-1].replace(",", "")
                    total_gross = decimals[-2].replace(",", "")

    if not total_net or not total_gross:
        all_weights = re.findall(r'\b\d{1,3}(?:,\d{3})*\.\d{3}\b', pdf_text)
        if len(all_weights) >= 2:
            total_net = all_weights[-1].replace(",", "")
            total_gross = all_weights[-2].replace(",", "")

    if not total_qty:
        qty_match = re.search(r'Total\D+(\d+)', pdf_text, re.IGNORECASE)
        if qty_match:
            total_qty = qty_match.group(1)

    extracted_items.append({
        "qty": int(total_qty) if total_qty and total_qty.isdigit() else 1,
        "net_weight": float(total_net) if total_net else 0.0,
        "gross_weight": float(total_gross) if total_gross else 0.0,
        "hs_code": combined_hscodes
    })
        
    if not extracted_items:
        extracted_items.append({
            "qty": 1,
            "net_weight": 0.0,
            "gross_weight": 0.0,
            "hs_code": ""
        })
        
    return extracted_items

def extract_bkt_header_value(pdf_bytes, keyword, field_label=""):
    """
    BKT Register के लेआउट के अनुसार X-Axis (Left < 135 vs Right >= 140) के आधार पर 
    पोर्ट और डिस्टिनेशन को 100% अलग करने वाला पार्सर नियम।
    """
    try:
        with pdfplumber.open(pdf_bytes) as pdf:
            page = pdf.pages[0]
            words = page.extract_words()
            full_kw = keyword.strip().lower()
            
            target_kw_words = []
            for w in words:
                if full_kw in w['text'].lower() or all(p in w['text'].lower() for p in full_kw.split()):
                    # यदि कीवर्ड 'destination' है, तो ऊपर वाले 'Country of final destination' (Top < 250) को छोड़ दें
                    if "destination" in full_kw and w['top'] < 250:
                        continue
                    target_kw_words.append(w)
            
            if target_kw_words:
                kw_word = target_kw_words[0]
                kw_y0 = kw_word['top']
                
                # कीवर्ड के ठीक नीचे मौजूद शब्दों को ढूंढना (Top range: 8 to 32 pixels below keyword)
                below_words = [w for w in words if kw_y0 + 8 <= w['top'] <= kw_y0 + 32]
                if below_words:
                    f_label = field_label.lower()
                    kw_lower = full_kw
                    
                    # 🛠️ पक्का कोऑर्डिनेट नियम:
                    if "destination" in f_label or "destination" in kw_lower or "final" in f_label:
                        # केवल दाहिना कॉलम (Final Destination) -> X0 >= 140
                        below_words = [w for w in below_words if w['x0'] >= 140]
                    elif "discharge" in f_label or "discharge" in kw_lower or "port" in f_label:
                        # केवल बायां कॉलम (Port of Discharge) -> X0 < 135
                        below_words = [w for w in below_words if w['x0'] < 135]
                    
                    below_words = sorted(below_words, key=lambda x: (round(x['top'] / 5), x['x0']))
                    extracted_below = " ".join([w['text'] for w in below_words]).strip()
                    
                    if extracted_below:
                        # डुप्लीकेट शब्द हटाने का लॉजिक
                        words_list = extracted_below.split()
                        unique_words = []
                        for w in words_list:
                            if not unique_words or unique_words[-1].lower() != w.lower():
                                unique_words.append(w)
                        n = len(unique_words)
                        if n % 2 == 0:
                            half = n // 2
                            if [w.lower() for w in unique_words[:half]] == [w.lower() for w in unique_words[half:]]:
                                unique_words = unique_words[:half]
                        return " ".join(unique_words).strip()
    except Exception:
        pass
    return ""

def map_items_to_excel_dynamic(
    ws, parsed_items, resolved_item_rules, 
    inv_sr_no=1, start_overall_sr=1, start_excel_row=2, 
    default_invoice_no="", default_invoice_date="", 
    pdf_text="", lut_kws="", paid_kws="", parser_rule="parser_bkt_register",
    pdf_bytes=None, mapping_rules=None, pdf_lines=None
):
    current_excel_row = start_excel_row
    overall_sr = start_overall_sr

    for item in parsed_items:
        for heading_name, rule_info in resolved_item_rules.items():
            col_letter = rule_info.get("col", "A").upper()
            rule_type = rule_info.get("type", "PDF Row Item")
            rule_val = rule_info.get("rule", "").strip()
            
            cell_ref = f"{col_letter}{current_excel_row}"
            h_upper = heading_name.upper()
            r_upper = rule_val.upper()
            
            if rule_type == "Constant Text":
                ws[cell_ref] = rule_val
            elif "NET" in h_upper or "NET" in r_upper:
                ws[cell_ref] = float(item.get("net_weight", 0.0))
            elif "GROSS" in h_upper or "GROSS" in r_upper:
                ws[cell_ref] = float(item.get("gross_weight", 0.0))
            elif "QTY" in h_upper or "QUANTITY" in h_upper or "QTY" in r_upper or "QUANTITY" in r_upper or "PACKAGES" in h_upper:
                ws[cell_ref] = int(item.get("qty", 0))
            elif "HS" in h_upper or "CODE" in h_upper or "HS" in r_upper or "CODE" in r_upper:
                ws[cell_ref] = item.get("hs_code", "")
            else:
                ws[cell_ref] = item.get("qty", 0)
                
        current_excel_row += 1
        overall_sr += 1

    max_r = ws.max_row
    if max_r > 2:
        row_map = {}
        for r in range(2, max_r + 1):
            cont_val = str(ws[f"L{r}"].value or "").strip()
            if cont_val:
                row_map.setdefault(cont_val, []).append(r)
        
        rows_to_delete = set()
        for cont, r_list in row_map.items():
            if len(r_list) > 1:
                primary_r = r_list[0]
                h_vals, i_vals, w_vals = [], [], []
                tot_net, tot_gross, tot_qty = 0.0, 0.0, 0
                
                for r in r_list:
                    val_h = str(ws[f"H{r}"].value or "").strip()
                    val_i = str(ws[f"I{r}"].value or "").strip()
                    val_w = str(ws[f"W{r}"].value or "").strip()
                    
                    if val_h and val_h not in h_vals: h_vals.append(val_h)
                    if val_i and val_i not in i_vals: i_vals.append(val_i)
                    if val_w:
                        for code in val_w.split(","):
                            c_clean = code.strip()
                            if c_clean and c_clean not in w_vals:
                                w_vals.append(c_clean)
                                
                    try: tot_net += float(ws[f"N{r}"].value or 0)
                    except: pass
                    try: tot_gross += float(ws[f"O{r}"].value or 0)
                    except: pass
                    try: tot_qty += int(ws[f"P{r}"].value or 0)
                    except: pass
                
                ws[f"H{primary_r}"] = ", ".join(h_vals)
                ws[f"I{primary_r}"] = ", ".join(i_vals)
                ws[f"W{primary_r}"] = ", ".join(w_vals)
                ws[f"N{primary_r}"] = round(tot_net, 3)
                ws[f"O{primary_r}"] = round(tot_gross, 3)
                ws[f"P{primary_r}"] = int(tot_qty)
                
                for r in r_list[1:]:
                    rows_to_delete.add(r)
        
        if rows_to_delete:
            all_data = []
            for r in range(2, ws.max_row + 1):
                if r not in rows_to_delete:
                    row_vals = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
                    if any(row_vals):
                        all_data.append(row_vals)
            
            for r in range(2, ws.max_row + 1):
                for c in range(1, ws.max_column + 1):
                    ws.cell(row=r, column=c).value = None
            
            write_r = 2
            for r_data in all_data:
                for c_idx, val in enumerate(r_data, start=1):
                    ws.cell(row=write_r, column=c_idx, value=val)
                write_r += 1
                
            current_excel_row = write_r
            overall_sr = start_overall_sr + len(all_data)

    return ws, overall_sr, current_excel_row
