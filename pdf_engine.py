if position == "box" and pdf_bytes and keyword:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page = pdf.pages[0]
                full_kw = keyword.strip().lower()
                words = page.extract_words()
                
                kw_word = None
                for w in words:
                    if w['top'] > 150:
                        if full_kw in w['text'].lower() or all(part in w['text'].lower() for part in full_kw.split()):
                            kw_word = w
                            break
                
                if not kw_word:
                    last_token = full_kw.split()[-1] if full_kw.split() else ""
                    for w in words:
                        if w['top'] > 150 and last_token and last_token in w['text'].lower():
                            kw_word = w
                            break
                
                if kw_word:
                    kw_x0 = kw_word['x0']
                    kw_y0 = kw_word['top']
                    
                    # सही चौड़ाई ताकि 'FOS SUR MER' पूरा आ जाए लेकिन दाहिना बॉक्स क्रॉस न हो
                    box_x0 = kw_x0 - 25
                    box_x1 = kw_x0 + 160
                    box_y0 = kw_y0 + 8
                    box_y1 = kw_y0 + 32
                    
                    box_words = [w for w in words if box_x0 <= w['x0'] <= box_x1 and box_y0 <= w['top'] <= box_y1]
                    if box_words:
                        box_words = sorted(box_words, key=lambda x: x['x0'])
                        
                        filtered_words = []
                        stop_text = str(stop_kw).strip().lower() if stop_kw else ""
                        
                        for w in box_words:
                            w_txt = w['text'].lower()
                            if stop_text and (stop_text in w_txt or w_txt.startswith(stop_text)):
                                break
                            filtered_words.append(w)
                            
                        extracted_box_text = " ".join([w['text'] for w in filtered_words]).strip()
                        if extracted_box_text:
                            return remove_duplicate_phrases(extracted_box_text)
        except Exception:
            pass
