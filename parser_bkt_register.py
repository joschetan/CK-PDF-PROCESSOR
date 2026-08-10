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
    
    # 1. सभी HS Codes ढूंढना (उदा: HS CODE#3: 40117000 या सीधे 40117000)
    hs_matches = re.findall(r'(?:HS\s*CODE[#\d\s:]*|CODE[#\s:]*)(\d{8})', pdf_text, re.IGNORECASE)
    if not hs_matches:
        # यदि सीधे 8 अंकों के कोड टेबल में दिए हों
        hs_matches = re.findall(r'\b(40\d{6})\b', pdf_text)
        
    for h in hs_matches:
        if h not in hs_codes_list:
            hs_codes_list.append(h)
            
    combined_hscodes = ", ".join(hs_codes_list) if hs_codes_list else ""

    # 2. टेबल की 'Total' वाली लाइन से Qty, Gross Weight और Net Weight ढूंढना
    for line in pdf_lines:
        clean_line = line.strip()
        # 'Total' या 'SUB TOTAL' वाली लाइन को पहचानना
        if clean_line.lower().startswith("total") or "total" in clean_line.lower():
            # अंकों और डेसिमल वाले आंकड़े ढूंढना
            numbers_in_line = re.findall(r'\b[\d,]+\.\d{3}\b|\b\d+\b', clean_line)
            if len(numbers_in_line) >= 3:
                # आमतौर पर आर्डर होता है: Qty, Gross Wt, Net Wt या इसी तरह
                # उदाहरण स्क्रीनशॉट के मुताबिक: Total | 74 | 8,522.20 | 1,955.360 | 1,955.360
                decimals = [n for n in numbers_in_line if '.' in n or ',' in n]
                ints = [n for n in numbers_in_line if '.' not in n and ',' not in n]
                
                if ints:
                    total_qty = ints[0]
                if len(decimals) >= 2:
                    total_net = decimals[-1].replace(",", "")
                    total_gross = decimals[-2].replace(",", "")

    # यदि लूप से टोटल वैल्यू न मिले तो regex से सीधे ढूंढने की कोशिश करें
    if not total_net or not total_gross:
        all_weights = re.findall(r'\b\d{1,3}(?:,\d{3})*\.\d{3}\b', pdf_text)
        if len(all_weights) >= 2:
            total_net = all_weights[-1].replace(",", "")
            total_gross = all_weights[-2].replace(",", "")

    if not total_qty:
        # 'Total' के पास वाली संख्या खोजने के लिए
        qty_match = re.search(r'Total\D+(\d+)', pdf_text, re.IGNORECASE)
        if qty_match:
            total_qty = qty_match.group(1)

    # एक्सट्रैक्ट किए गए डेटा को आइटम डिक्शनरी में रखना ताकि डायनामिक मैपिंग इसका उपयोग कर सके
    extracted_items.append({
        "description": combined_hscodes, # या डिफ़ॉल्ट डिस्क्रिप्शन
        "qty": total_qty if total_qty else "0",
        "net_weight": total_net,
        "gross_weight": total_gross,
        "hs_code": combined_hscodes
    })
        
    # अगर किसी वजह से आइटम खाली रहे तो डिफ़ॉल्ट रिटर्न करें
    if not extracted_items:
        extracted_items.append({
            "description": "Default Item / Description",
            "qty": "1",
            "rate": "0",
            "amount": "0"
        })
        
    return extracted_items

def map_items_to_excel_dynamic(
    ws, parsed_items, resolved_item_rules, 
    inv_sr_no=1, start_overall_sr=1, start_excel_row=2, 
    default_invoice_no="", default_invoice_date="", 
    pdf_text="", lut_kws="", paid_kws="", parser_rule="parser_bkt_register"
):
    """
    यूजर द्वारा बनाए गए डायनामिक कॉलम रूल्स (Column Builder) के अनुसार 
    Net Weight, Gross Weight, Quantity और H S Code को सही एक्सेल कॉलम में मैप करता है।
    """
    current_excel_row = start_excel_row
    overall_sr = start_overall_sr

    for item in parsed_items:
        for heading_name, rule_info in resolved_item_rules.items():
            col_letter = rule_info.get("col", "A").upper()
            rule_type = rule_info.get("type", "PDF Row Item")
            rule_val = rule_info.get("rule", "")
            
            cell_ref = f"{col_letter}{current_excel_row}"
            
            # यूजर के दिए गए हेडिंग नाम या नियम के आधार पर सही वैल्यू फिल करना
            h_lower = heading_name.lower()
            
            if rule_type == "Constant Text":
                ws[cell_ref] = rule_val
            elif "net" in h_lower:
                ws[cell_ref] = item.get("net_weight", "")
            elif "gross" in h_lower:
                ws[cell_ref] = item.get("gross_weight", "")
            elif "qty" in h_lower or "quantity" in h_lower:
                ws[cell_ref] = item.get("qty", "")
            elif "hs" in h_lower or "code" in h_lower:
                ws[cell_ref] = item.get("hs_code", "")
            else:
                # डिफ़ॉल्ट फॉलबैक
                ws[cell_ref] = item.get("description", "")
                
        current_excel_row += 1
        overall_sr += 1

    return ws, overall_sr, current_excel_row
