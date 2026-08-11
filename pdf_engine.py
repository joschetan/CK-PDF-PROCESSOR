# 📦 3. TRUE BOUNDARY-AWARE 'box' OPTION (pdfplumber की असली टेबल बाउंड्री के साथ)
    if position == "box" and pdf_bytes and keyword:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page = pdf.pages[0]
                full_kw = keyword.strip().lower()
                
                # 1. pdfplumber से पेज की सभी टेबल्स और उनके सेल्स (Cells/Boxes) ढूँढना
                tables = page.extract_tables()
                target_cell_text = None
                
                # अगर टेबल्स नहीं मिलती हैं, तो लाइन-आधारિત बाउंड्री का उपयोग करेंगे
                table_objs = page.find_tables()
                
                matched_bbox = None
                for table in table_objs:
                    for row in table.extract():
                        for cell in row:
                            if cell and full_kw in cell.lower():
                                # अब इस सेल के ठीक नीचे वाले सेल या उसी सेल के अंदर की वैल्यू तलाशनी है
                                pass

                # 2. शब्दों के कोऑर्डिनेट्स और असली PDF लाइनों (Rectangles/Lines) का उपयोग करके बाउंड्री निकालना
                words = page.extract_words()
                kw_word = None
                
                lines_map = {}
                for w in words:
                    ly = round(w['top'] / 5) * 5
                    lines_map.setdefault(ly, []).append(w)
                
                for ly in sorted(lines_map.keys()):
                    line_words = sorted(lines_map[ly], key=lambda x: x['x0'])
                    line_str = " ".join([w['text'] for w in line_words]).lower()
                    if full_kw in line_str:
                        for w in line_words:
                            if full_kw.split()[-1] in w['text'].lower() or full_kw.split()[0] in w['text'].lower():
                                kw_word = w
                                break
                        if kw_word:
                            break
                
                if kw_word:
                    kw_x0 = kw_word['x0']
                    kw_y0 = kw_word['top']
                    
                    # 3. अब हम PDF की असली होरिजेंटल (Horizontal) लाइनों को ढूँढेंगे जो इस कीवर्ड के नीचे और ऊपर हैं
                    # इससे हमें डिब्बे की सटीक ऊँचाई (Height) मिल जाएगी और नीचे वाली टेबल कभी बीच में नहीं आएगी
                    edges = page.edges + page.curves + [{'x0': l['x0'], 'top': l['top'], 'x1': l['x1'], 'bottom': l['bottom']} for l in page.extract_lines()]
                    
                    # डिब्बे की निचली सीमा तय करने के लिए कीवर्ड के तुरंत बाद आने वाली होरिजेंटल लाइन ढूँढें
                    next_bottom_y = kw_y0 + 35  default limit
                    for line in page.extract_lines():
                        if line['top'] > kw_y0 + 5 and line['top'] < kw_y0 + 60:
                            if abs(line['x0'] - kw_x0) < 50 or line['x0'] <= kw_x0 <= line['x1']:
                                next_bottom_y = line['top']
                                break
                    
                    # सख्त बाउंड्री: कीवर्ड के नीचे और मिली हुई लाइन के ऊपर का एरिया ही सिर्फ स्कैन होगा
                    box_x0 = kw_x0 - 15
                    box_x1 = kw_x0 + 180
                    box_y0 = kw_y0 + 8
                    box_y1 = next_bottom_y - 2  # कभी भी नीचे वाली लाइन को पार नहीं करेगा!
                    
                    box_words = [w for w in words if box_x0 <= w['x0'] <= box_x1 and box_y0 <= w['top'] <= box_y1]
                    if box_words:
                        box_words = sorted(box_words, key=lambda x: (round(x['top'] / 5), x['x0']))
                        extracted_box_text = " ".join([w['text'] for w in box_words]).strip()
                        if extracted_box_text:
                            return extracted_box_text
        except Exception:
            pass
