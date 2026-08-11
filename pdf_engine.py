# 📦 3. NEW 'box' OPTION (स्पेस और मल्टी-वर्ड कीवर्ड के साथ पूरी लाइन खींचने हेतु)
    if position == "box" and pdf_bytes and keyword:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page = pdf.pages[0]
                words = page.extract_words()
                
                # कीवर्ड के शब्दों को अलग करके पहला शब्द ढूँढना (जैसे 'Port')
                kw_parts = keyword.strip().split()
                first_kw = kw_parts[0].lower() if kw_parts else ""
                
                kw_word = None
                for w in words:
                    if first_kw and first_kw in w['text'].lower():
                        kw_word = w
                        break
                
                if kw_word:
                    kw_x0 = kw_word['x0']
                    kw_y0 = kw_word['top']
                    
                    # पोर्ट वाले छोटे बॉक्स के अंदर का क्षेत्र (कीवर्ड के ठीक नीचे)
                    box_x0 = kw_x0 - 15
                    box_x1 = kw_x0 + 220
                    box_y0 = kw_y0 + 8
                    box_y1 = kw_y0 + 42
                    
                    box_words = [w for w in words if box_x0 <= w['x0'] <= box_x1 and box_y0 <= w['top'] <= box_y1]
                    if box_words:
                        box_words = sorted(box_words, key=lambda x: (round(x['top'] / 5), x['x0']))
                        return " ".join([w['text'] for w in box_words]).strip()
        except Exception:
            pass
