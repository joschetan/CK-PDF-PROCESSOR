# 3. Horizontal Scrollable Excel Header Configuration (Fixed Layout)
        st.write("---")
        c_eh_head, c_eh_btn = st.columns([7, 3])
        with c_eh_head:
            st.subheader("📊 Excel Download Header Configuration")
            st.caption("कॉलम जोड़ते जाएं, हॉरिजॉन्टल स्क्रॉल बार अपने आप आ जाएगा:")
        with c_eh_btn:
            if st.button("➕ Add Header", use_container_width=True):
                add_excel_header_dialog(selected_shipper)
        
        if "excel_headers" not in shipper_info:
            shipper_info["excel_headers"] = {"Invoice No": "A", "Date": "B"}
            
        updated_excel_headers = {}
        header_items = list(shipper_info["excel_headers"].items())
        
        # 🚀 सुधार: Custom CSS for Horizontal Scrolling
        st.markdown(
            """
            <style>
            .scroll-wrapper {
                display: flex;
                overflow-x: auto;
                gap: 15px;
                padding-bottom: 15px;
                width: 100%;
                white-space: nowrap;
            }
            .header-card-fixed {
                min-width: 200px;
                background: #f8f9fa;
                padding: 10px;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # Container starts here
        st.markdown('<div class="scroll-wrapper">', unsafe_allow_html=True)
        
        for idx, (h_name, h_col) in enumerate(header_items):
            # एक ही बॉक्स के अंदर हेडर नेम और कॉलम लेटर
            st.markdown('<div class="header-card-fixed">', unsafe_allow_html=True)
            e_hname = st.text_input("H", value=h_name, key=f"eh_{idx}", label_visibility="collapsed")
            sub_c1, sub_c2 = st.columns([3, 1])
            with sub_c1:
                e_hcol = st.text_input("C", value=h_col, key=f"ec_{idx}", label_visibility="collapsed").upper()
            with sub_c2:
                if st.button("🗑️", key=f"del_eh_{idx}"):
                    del shipper_info["excel_headers"][h_name]
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            updated_excel_headers[e_hname] = e_hcol
            
        st.markdown('</div>', unsafe_allow_html=True)
        shipper_info["excel_headers"] = updated_excel_headers
