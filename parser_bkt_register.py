import re
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
    
    # 1. सभी HS Codes ढूंढना
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
        "qty": total_qty if total_qty else "0",
        "net_weight": total_net,
        "gross_weight": total_gross,
        "hs_code": combined_hscodes
    })
        
    if not extracted_items:
        extracted_items.append({
            "qty": "1",
            "net_weight": "0",
            "gross_weight": "0",
            "hs_code": ""
        })
        
    return extracted_items

def map_items_to_excel_dynamic(
    ws, parsed_items, resolved_item_rules, 
    inv_sr_no=1, start_overall_sr=1, start_excel_row=2, 
    default_invoice_no="", default_invoice_date="", 
    pdf_text="", lut_kws="", paid_kws="", parser_rule="parser_bkt_register"
):
    """
    यूजर द्वारा बनाए गए आइटम टेबल कॉलम रूल्स (Item Field Name) के अनुसार 
    सटीक Excel Col पर सही डेटा मैप करता है।
    """
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
                ws[cell_ref] = item.get("net_weight", "")
            elif "GROSS" in h_upper or "GROSS" in r_upper:
                ws[cell_ref] = item.get("gross_weight", "")
            elif "QTY" in h_upper or "QUANTITY" in h_upper or "QTY" in r_upper or "QUANTITY" in r_upper or "PACKAGES" in h_upper:
                ws[cell_ref] = item.get("qty", "")
            elif "HS" in h_upper or "CODE" in h_upper or "HS" in r_upper or "CODE" in r_upper:
                ws[cell_ref] = item.get("hs_code", "")
            else:
                ws[cell_ref] = item.get("qty", "")
                
        current_excel_row += 1
        overall_sr += 1

    return ws, overall_sr, current_excel_row
