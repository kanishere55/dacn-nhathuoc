"""Nguồn ảnh thật (không phải ảnh do AI sinh) cho thuốc và chi nhánh.

Mọi ảnh là ảnh chụp thật trên Wikimedia Commons với giấy phép mở (CC0, CC BY, CC BY-SA hoặc phạm vi
công cộng). Lệnh `nap_anh_that` tải về, kiểm SHA-256, chuẩn hóa WebP rồi lưu bytea trong PostgreSQL
kèm tác giả, giấy phép và đường dẫn nguồn để ghi công theo yêu cầu của giấy phép.

Mỗi thuốc có một bộ ảnh (ANH_THUOC là ảnh đầu, ANH_THUOC_THEM là các ảnh sau) để trang chi tiết có
ảnh trượt. Mỗi ảnh là ảnh chụp đúng sản phẩm, đúng nhãn hiệu hoặc cùng hoạt chất (ví dụ viên diclofenac
50 mg, Voltaren 50 mg). Mức khớp được ghi ở MUC_KHOP và hiện thành ghi chú trước dòng nguồn ảnh, để
người xem biết ảnh nào chỉ là minh họa. Hapacol và Efferalgan chưa có ảnh mở đúng sản phẩm nên dùng ảnh
viên paracetamol (cùng hoạt chất); quản trị có thể tải ảnh chụp bao bì thật lên thay thế.
"""

ANH_THUOC = {
    "TA-PANADOL-500": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/07/Panadol_500_mg.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "891c62e0e206d294d7a13bed5ca0dc8eaaa9c738400327bb77b3fe468b2d06e8",
        "tac_gia": "JIP",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Panadol_500_mg.jpg",
    },
    "TA-ASPIRIN-PH8": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/8/8e/Acylpyrin.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "b2cda33c6754e83f8b0a182f5dcab390f17c56c85887f924c8325c7860b7235d",
        "tac_gia": "Marcus33",
        "giay_phep": "Public domain",
        "trang": "https://commons.wikimedia.org/wiki/File:Acylpyrin.jpg",
    },
    "TA-VOLTAREN-50": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/be/Voltaren_tablets.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "93e75dceb3f8526c2c95e6e123388465122d9e2b8a81bcf2e325de99500e4eca",
        "tac_gia": "Editor182 (talk)",
        "giay_phep": "Public domain",
        "trang": "https://commons.wikimedia.org/wiki/File:Voltaren_tablets.jpg",
    },
    "TA-GOFEN-400": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/7a/Ibuprofen-400.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "ab4e3c73b536b8ac64a4eb22b3c0f2bd054f396097577b8b2e7bf181bc33ec9b",
        "tac_gia": "Wesalius",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Ibuprofen-400.jpg",
    },
    "TA-SALONPAS-20": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a6/Salonpas_Pain_Relieving_Patch.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "93944106072786793b8a469ec1f5b6b0ef986f274bffa02e77893ffabe3cf9db",
        "tac_gia": "AddisWang",
        "giay_phep": "CC BY-SA 3.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Salonpas_Pain_Relieving_Patch.jpg",
    },
    "TA-ATARAX-25": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/5/52/Polish_Hydroxizinum_Espefa_%28hydroxizine%29_tablets%2C_25_mg.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "c8ab14a6cd3211c15086a78d17f3755119729a69fed1001170cd4d44adcb64c7",
        "tac_gia": "Żółwiciel",
        "giay_phep": "CC BY-SA 3.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Polish_Hydroxizinum_Espefa_(hydroxizine)_tablets,_25_mg.jpg",
    },
    "TA-STILNOX-10": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a3/Stilnox_sales_in_China.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "41440482b98e413379c2ffe80fffc4421114f0ce98b55c0799f486f55adb445b",
        "tac_gia": "Zhanglide",
        "giay_phep": "CC0",
        "trang": "https://commons.wikimedia.org/wiki/File:Stilnox_sales_in_China.jpg",
    },
    "TA-VENTOLIN-INH": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/e/ed/Ventolin_Inhaler_N_100_ug_inh.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "0f194b2cf1ee1d9faa642ed4ba5c6b8ce1a67a0c6d8367789f34125f36448594",
        "tac_gia": "Tomino de WS",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Ventolin_Inhaler_N_100_ug_inh.jpg",
    },
    "TA-ZYRTEC-10": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/c/cf/Cetirizine_tablets_under_the_brand_name_%C2%AB%D0%97%D0%BE%D0%B4%D0%B0%D0%BA%C2%BB.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "bb029f9fde8933b593854054db8e96fe961679b3c1446bf4c1618fb6d7df716a",
        "tac_gia": "Issuial",
        "giay_phep": "CC0",
        "trang": "https://commons.wikimedia.org/wiki/File:Cetirizine_tablets_under_the_brand_name_%C2%AB%D0%97%D0%BE%D0%B4%D0%B0%D0%BA%C2%BB.jpg",
    },
    "TA-CLARITYNE-10": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/2/2d/Fortune_NT-Alergi_tablet_%28contains_Loratadine_10mg%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "9e2b4b9bb043ed789b3b2828ac163b15978ca4224b9c32ef8b41273ad3360a49",
        "tac_gia": "Mk2010",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Fortune_NT-Alergi_tablet_(contains_Loratadine_10mg).jpg",
    },
    "TA-STREPSILS-24": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/b2/Israeli_Strepsils_Package.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "f7ad873a57f1179a500bda92ea20b7f650072c8e12425ce3f5f63f1ea371e6c2",
        "tac_gia": "Horizon206",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Israeli_Strepsils_Package.jpg",
    },
    "TA-BISOLVON-8": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/e/e1/%D0%91%D0%A0%D0%9E%D0%9C%D0%93%D0%95%D0%9A%D0%A1%D0%98%D0%9D-%D0%A3%D0%91%D0%A4.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "8f7a899b7ec2b4b2d7c0245130c4fdf399e1726dc397f8d56861c751a8959132",
        "tac_gia": "Schekinov Alexey Victorovich",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:%D0%91%D0%A0%D0%9E%D0%9C%D0%93%D0%95%D0%9A%D0%A1%D0%98%D0%9D-%D0%A3%D0%91%D0%A4.jpg",
    },
    "TA-ACEMUC-200": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/bd/Fluimucil_NAC_pills_in_China.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "7211722e2ed1f548828bc5669ba8fa12b33d11cda4d52787930c75148113d602",
        "tac_gia": "Vack Xu",
        "giay_phep": "CC0",
        "trang": "https://commons.wikimedia.org/wiki/File:Fluimucil_NAC_pills_in_China.jpg",
    },
    "TA-SMECTA-30": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/f/f6/%E8%88%92%E8%85%B9%E9%81%94%28Smecta%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "6d3216cdc046b5cf63980d90d6e7ddd9a77f8c019e63d2464e8f0246fddf65c6",
        "tac_gia": "R1235613",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:%E8%88%92%E8%85%B9%E9%81%94(Smecta).jpg",
    },
    "TA-IMODIUM-2": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/7b/Imodium.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "b476c0159bef1f395b6850ac03624377ea27535002128c935d1fe3dc45652909",
        "tac_gia": "Xapkov",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Imodium.jpg",
    },
    "TA-ENTEROGERMINA-20": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/3/3c/Enterogermina.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "57dafec1574c9148309d49409fe1014950e0201951887811c3b7f69c745582b6",
        "tac_gia": "Gizem Oktay",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Enterogermina.jpg",
    },
    "TA-REDOXON-1000": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/b7/Redoxon_Double_Action_Vitamin_C_standard_tablets.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "10581c55b965f6c68b7b6429672e28a8bcbba46e55858f600a30d00b4e1643e3",
        "tac_gia": "Hypersonic man 11",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Redoxon_Double_Action_Vitamin_C_standard_tablets.jpg",
    },
    "TA-BEROCCA-10": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/6/68/Berocca_tablet_and_drink.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "e1d329a234aaec7ae1689b030583c3fc75db505f2a82297adfa6f17775059a24",
        "tac_gia": "Sgroey",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Berocca_tablet_and_drink.jpg",
    },
    "TA-PHOSPHALUGEL-26": {
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a8/%D0%A4%D0%BE%D1%81%D1%84%D0%B0%D0%BB%D1%8E%D0%B3%D0%B5%D0%BB%D1%8C.jpg/1920px-%D0%A4%D0%BE%D1%81%D1%84%D0%B0%D0%BB%D1%8E%D0%B3%D0%B5%D0%BB%D1%8C.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
        "sha256": "bdf265cc186f8c59c1f26af8460ad50019071fda4b8aeaab5a84b72e23f0a07c",
        "tac_gia": "BarbariSka88",
        "giay_phep": "CC0",
        "trang": "https://commons.wikimedia.org/wiki/File:%D0%A4%D0%BE%D1%81%D1%84%D0%B0%D0%BB%D1%8E%D0%B3%D0%B5%D0%BB%D1%8C.jpg",
    },
    "TA-EFFERALGAN-500": {
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e5/Paracetamol_acetaminophen_500_mg_pills.jpg/1920px-Paracetamol_acetaminophen_500_mg_pills.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
        "sha256": "0bb0e126ba3cc9d78250717ee2baf4498595579cbfc8a606d3b428375087d859",
        "tac_gia": "Michelle Tribe from Ottawa, Canada",
        "giay_phep": "CC BY 2.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Paracetamol_acetaminophen_500_mg_pills.jpg",
    },
    "TA-HAPACOL-250": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a5/Medication_Paracetamol.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "5ee128b911056d3b576042d4da3492492d52be24e3b9a56e789c7c8934617875",
        "tac_gia": "Mk2010",
        "giay_phep": "CC BY-SA 3.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Medication_Paracetamol.JPG",
    },
    "TA-BETADINE-125": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Betadine.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "327377897571b99b71b0add0be00d791f5b6dddb9d55fe5434008bff4700db36",
        "tac_gia": "Aneta Crsová",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Betadine.jpg",
    },
}

# Chi nhánh là mô phỏng nên dùng ảnh chụp nhà thuốc thật làm minh họa; ghép theo NHOM_CHI_NHANH bên dưới.
ANH_CHI_NHANH = [
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/8/8c/Interior_of_Sunlight_Pharmacy%2C_105_Richmond_Road%2C_Gillingham_ME71LX_-_Medway.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "388174b274c6dcab449dff9e6bef5b2cc37b3a5e7369c6fc24f926e358ff8ad3",
        "tac_gia": "Sunolafjagtenben-hur",
        "giay_phep": "CC0",
        "trang": "https://commons.wikimedia.org/wiki/File:Interior_of_Sunlight_Pharmacy,_105_Richmond_Road,_Gillingham_ME71LX_-_Medway.jpg",
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/8/8d/Nh%C3%A0_thu%E1%BB%91c%2C_6_Qu%C3%A1n_S%E1%BB%A9%2C_H%C3%A0_N%E1%BB%99i_001.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "d3f8258eac77c5220df0564e53ce3ac6f62d9c4616787fe6561cb532982e7bac",
        "tac_gia": "Phan Minh Tuấn",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Nh%C3%A0_thu%E1%BB%91c,_6_Qu%C3%A1n_S%E1%BB%A9,_H%C3%A0_N%E1%BB%99i_001.JPG",
    },
    {
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/2d/Brest_Greenberg_Pharmacy_Interior_2024-09-20_3798.jpg/1920px-Brest_Greenberg_Pharmacy_Interior_2024-09-20_3798.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
        "sha256": "ed071eab6af8c101f59a73d70b499bc99f5a27394d7e72851bde91b61abd9c71",
        "tac_gia": "Mike1979 Russia",
        "giay_phep": "CC BY-SA 3.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Brest_Greenberg_Pharmacy_Interior_2024-09-20_3798.jpg",
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Castellon_pharmacy_New_Orleans_-_interior_Oct_2023.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "sha256": "4fcd8432aab31bae0ff0bfd39cbe12ba1c9525f9e5a09250641f1d119253f061",
        "tac_gia": "Infrogmation of New Orleans",
        "giay_phep": "CC BY-SA 2.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Castellon_pharmacy_New_Orleans_-_interior_Oct_2023.jpg",
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/4/43/Section_of_drug_store_in_Nigeria.jpg",
        "sha256": "c63e1ab7a58ce7e32c3f0b21bdd2b784567760f2f650ca0785fce67b7a4db4ae",
        "tac_gia": "Beendy234",
        "giay_phep": "CC BY 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Section_of_drug_store_in_Nigeria.jpg",
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Brest_Greenberg_Pharmacy_Interior_2024-09-20_3797.jpg/1920px-Brest_Greenberg_Pharmacy_Interior_2024-09-20_3797.jpg",
        "sha256": "441c4b41a18e6b3a5541efaa3b4078bc78582f0884a46ac203947cba1d1c2ee7",
        "tac_gia": "Mike1979 Russia",
        "giay_phep": "CC BY-SA 3.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Brest_Greenberg_Pharmacy_Interior_2024-09-20_3797.jpg",
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/b5/Brest_Greenberg_Pharmacy_2024-09-17_3616.jpg",
        "sha256": "1c4dc69db649e22b2768497224e493b5208c3299c81b227cc7f9ca7bc7120677",
        "tac_gia": "Mike1979 Russia",
        "giay_phep": "CC BY-SA 3.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Brest_Greenberg_Pharmacy_2024-09-17_3616.jpg",
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/72/Castellon_Pharmacy_New_Orleans_Entrance_May_2020.jpg",
        "sha256": "34fef655a2c8ec0fe2635fb2a9199224b0bc2f9ddfa03ddba57581df9d670766",
        "tac_gia": "Infrogmation of New Orleans",
        "giay_phep": "CC BY-SA 4.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Castellon_Pharmacy_New_Orleans_Entrance_May_2020.jpg",
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/de/Castellon_Pharmacy%2C_New_Orleans%2C_interior%2C_19_Sept_2024_-_1.jpg",
        "sha256": "802fb396e02b10918db7c0b0dc61e4ee1f3772c09716f7cc3801a3dc8373a48d",
        "tac_gia": "Infrogmation of New Orleans",
        "giay_phep": "CC BY-SA 2.0",
        "trang": "https://commons.wikimedia.org/wiki/File:Castellon_Pharmacy,_New_Orleans,_interior,_19_Sept_2024_-_1.jpg",
    },
]

# Mức khớp của ảnh với sản phẩm; hiện thành ghi chú đầu dòng nguồn để khách và hội đồng không hiểu nhầm.
KHOP_SAN_PHAM = "san_pham"  # đúng sản phẩm, đúng quy cách
KHOP_NHAN_HIEU = "nhan_hieu"  # đúng nhãn hiệu, bao bì hoặc quy cách có thể khác
KHOP_HOAT_CHAT = "hoat_chat"  # cùng hoạt chất, khác nhãn hiệu (hàm lượng, dạng bào chế có thể khác)
GHI_CHU_KHOP = {
    KHOP_SAN_PHAM: "",
    KHOP_NHAN_HIEU: "Ảnh minh họa cùng nhãn hiệu, bao bì hoặc quy cách có thể khác · ",
    KHOP_HOAT_CHAT: "Ảnh minh họa cùng hoạt chất, không phải bao bì sản phẩm này · ",
}
MUC_KHOP = {
    "TA-VOLTAREN-50": KHOP_SAN_PHAM,
    "TA-SALONPAS-20": KHOP_SAN_PHAM,
    "TA-STILNOX-10": KHOP_SAN_PHAM,
    "TA-VENTOLIN-INH": KHOP_SAN_PHAM,
    "TA-STREPSILS-24": KHOP_SAN_PHAM,
    "TA-SMECTA-30": KHOP_SAN_PHAM,
    "TA-ENTEROGERMINA-20": KHOP_SAN_PHAM,
    "TA-PANADOL-500": KHOP_NHAN_HIEU,
    "TA-BETADINE-125": KHOP_NHAN_HIEU,
    "TA-REDOXON-1000": KHOP_NHAN_HIEU,
    "TA-BEROCCA-10": KHOP_NHAN_HIEU,
    "TA-IMODIUM-2": KHOP_NHAN_HIEU,
    "TA-PHOSPHALUGEL-26": KHOP_NHAN_HIEU,
    "TA-ASPIRIN-PH8": KHOP_HOAT_CHAT,
    "TA-GOFEN-400": KHOP_HOAT_CHAT,
    "TA-ATARAX-25": KHOP_HOAT_CHAT,
    "TA-ZYRTEC-10": KHOP_HOAT_CHAT,
    "TA-CLARITYNE-10": KHOP_HOAT_CHAT,
    "TA-BISOLVON-8": KHOP_HOAT_CHAT,
    "TA-ACEMUC-200": KHOP_HOAT_CHAT,
    "TA-EFFERALGAN-500": KHOP_HOAT_CHAT,
    "TA-HAPACOL-250": KHOP_HOAT_CHAT,
}
GHI_CHU_CHI_NHANH = "Ảnh minh họa nhà thuốc, không phải cơ sở thật của chi nhánh này · "

# Ảnh thứ hai trở đi của thuốc (bộ ảnh trượt trên trang chi tiết); mỗi ảnh tự ghi mức khớp.
ANH_THUOC_THEM = {
    "TA-PANADOL-500": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/d/d7/%D0%9F%D0%B0%D1%80%D0%B0%D1%86%D0%B5%D1%82%D0%B0%D0%BC%D0%BE%D0%BB%2C_%D0%A4%D0%B0%D1%80%D0%BC%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82_%D0%9A%D1%83%D1%80%D1%81%D0%BA_%28Paracetamol%29_03.jpg",
            "sha256": "7ce9f34c120892d53447da091ee59fbb77ce1caae86c1cb265ffb0254aa5ec48",
            "tac_gia": "Retired electrician",
            "giay_phep": "CC0",
            "trang": "https://commons.wikimedia.org/wiki/File:%D0%9F%D0%B0%D1%80%D0%B0%D1%86%D0%B5%D1%82%D0%B0%D0%BC%D0%BE%D0%BB,_%D0%A4%D0%B0%D1%80%D0%BC%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82_%D0%9A%D1%83%D1%80%D1%81%D0%BA_(Paracetamol)_03.jpg",
            "khop": KHOP_HOAT_CHAT,
        }
    ],
    "TA-ASPIRIN-PH8": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/3/32/Big_Aspirin_Bottle.jpg",
            "sha256": "e7b458e73a9e37ecfdb653bbfe9c2311c825f28c1601574f738aaaf59f79b765",
            "tac_gia": "Grantmidnight",
            "giay_phep": "CC BY-SA 4.0",
            "trang": "https://commons.wikimedia.org/wiki/File:Big_Aspirin_Bottle.jpg",
            "khop": KHOP_HOAT_CHAT,
        }
    ],
    "TA-VOLTAREN-50": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/2/29/Diclofenac_Natrium_50mg_Aurobindo.jpg",
            "sha256": "1e4a5732ab11cdaf5100aa6d88ef038359eec2c859fab09d32d83287f9ef75d6",
            "tac_gia": "Bluberryman",
            "giay_phep": "CC BY 4.0",
            "trang": "https://commons.wikimedia.org/wiki/File:Diclofenac_Natrium_50mg_Aurobindo.jpg",
            "khop": KHOP_HOAT_CHAT,
        }
    ],
    "TA-GOFEN-400": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/8/85/Ibalgin-400.jpg",
            "sha256": "d8482e79a941e48b16fbf235718fd18a0d92c9323db6dd437d60f6159f219464",
            "tac_gia": "Wesalius",
            "giay_phep": "CC BY-SA 4.0",
            "trang": "https://commons.wikimedia.org/wiki/File:Ibalgin-400.jpg",
            "khop": KHOP_HOAT_CHAT,
        }
    ],
    "TA-ATARAX-25": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Spilled_Hydroxyzine_tablets.jpg/1920px-Spilled_Hydroxyzine_tablets.jpg",
            "sha256": "a332aaafee9e2887fd7a6ccc670552a8e30ceb1c19f822c98bd197863cf97055",
            "tac_gia": "Candeadly",
            "giay_phep": "CC BY 4.0",
            "trang": "https://commons.wikimedia.org/wiki/File:Spilled_Hydroxyzine_tablets.jpg",
            "khop": KHOP_HOAT_CHAT,
        }
    ],
    "TA-STILNOX-10": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/5/54/Kc-zolpidem-10mg.jpg",
            "sha256": "f0d2d1bb72d59cd82706001818035547f086e7c28a01ae9eedf204ddd90096a5",
            "tac_gia": "Freakinout",
            "giay_phep": "CC0",
            "trang": "https://commons.wikimedia.org/wiki/File:Kc-zolpidem-10mg.jpg",
            "khop": KHOP_HOAT_CHAT,
        }
    ],
    "TA-VENTOLIN-INH": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/b/b4/Ventolin_CFC.JPG",
            "sha256": "e20c2a5dc946fe1043dc2409437a3f371e859dfdb9c3c8d5a137f8a18597382a",
            "tac_gia": "Pokrajac",
            "giay_phep": "CC BY-SA 3.0",
            "trang": "https://commons.wikimedia.org/wiki/File:Ventolin_CFC.JPG",
            "khop": KHOP_NHAN_HIEU,
        }
    ],
    "TA-ZYRTEC-10": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/f/f2/Cetirizine_-_by_Danny_S.jpg",
            "sha256": "cc7f7d86dc3e91f1cbaffe523a05582a0878df06d837e60f0bccdcd32fd0de2e",
            "tac_gia": "Danny S.",
            "giay_phep": "CC BY-SA 3.0",
            "trang": "https://commons.wikimedia.org/wiki/File:Cetirizine_-_by_Danny_S.jpg",
            "khop": KHOP_HOAT_CHAT,
        }
    ],
    "TA-STREPSILS-24": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/0/0d/Strepsils_in_Egypt.jpg",
            "sha256": "acf46a86821e98ecba8a6012321f41c15260fb6c42cd934f12b6154890bc0ffc",
            "tac_gia": "Reem Al-Kashif",
            "giay_phep": "CC BY-SA 4.0",
            "trang": "https://commons.wikimedia.org/wiki/File:Strepsils_in_Egypt.jpg",
            "khop": KHOP_NHAN_HIEU,
        }
    ],
    "TA-SMECTA-30": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/8/88/Diosmectite_Mylan_3g.jpg",
            "sha256": "53f4c1ac64ef4405132706a37aa622ec601f4cd7b516fd582d9b82e50ddf25d6",
            "tac_gia": "Torfanomazine",
            "giay_phep": "CC0",
            "trang": "https://commons.wikimedia.org/wiki/File:Diosmectite_Mylan_3g.jpg",
            "khop": KHOP_HOAT_CHAT,
        }
    ],
    "TA-ENTEROGERMINA-20": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/07475jfBacillus_clausii_Erceflorafvf_05.jpg",
            "sha256": "c6c326527edc031b02bf076c38232d88efed219c85d10be0b752c506e98d0ab0",
            "tac_gia": "Judgefloro",
            "giay_phep": "CC0",
            "trang": "https://commons.wikimedia.org/wiki/File:07475jfBacillus_clausii_Erceflorafvf_05.jpg",
            "khop": KHOP_HOAT_CHAT,
        }
    ],
    "TA-BEROCCA-10": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/4/48/Berocca_Varieties.jpg",
            "sha256": "5f25b43e8668893b3e70adf239c31ab4f733ce662f4e98db854a2193ac801c66",
            "tac_gia": "MichaelGG at English Wikipedia",
            "giay_phep": "Public domain",
            "trang": "https://commons.wikimedia.org/wiki/File:Berocca_Varieties.jpg",
            "khop": KHOP_NHAN_HIEU,
        }
    ],
    "TA-IMODIUM-2": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/8/83/2023_Loperamid_2_mg.jpg",
            "sha256": "eb810f682f397e6addaec2ac175dba04c1d5a3b77feeddb2e0bc3c54f989ed1d",
            "tac_gia": "Jacek Halicki",
            "giay_phep": "CC BY-SA 4.0",
            "trang": "https://commons.wikimedia.org/wiki/File:2023_Loperamid_2_mg.jpg",
            "khop": KHOP_HOAT_CHAT,
        }
    ],
    "TA-BETADINE-125": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/c/cc/Betadine_spray.jpg",
            "sha256": "dc525740cc232c958d06da7e642440c3b6dc7610c4337dc67ba689167670fd2a",
            "tac_gia": "Whispyhistory",
            "giay_phep": "CC BY-SA 4.0",
            "trang": "https://commons.wikimedia.org/wiki/File:Betadine_spray.jpg",
            "khop": KHOP_NHAN_HIEU,
        }
    ],
}

# Chi nhánh thứ i (theo mã chi nhánh) nhận các ảnh ANH_CHI_NHANH ở vị trí NHOM_CHI_NHANH[i], theo thứ tự.
NHOM_CHI_NHANH = [[0, 1, 4], [2, 5, 6], [3, 7, 8]]
