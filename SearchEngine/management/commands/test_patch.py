import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_logic(target_id):
    # Kita pake verb 'GetRecord' bukan 'ListRecords' biar lgsg kena target
    oai_id = f"oai:digilib.unila.ac.id:{target_id}"
    url = f"https://digilib.unila.ac.id/cgi/oai2?verb=GetRecord&metadataPrefix=oai_dc&identifier={oai_id}"
    
    print(f"[*] Mengetes ID: {target_id}")
    print(f"[*] URL Target: {url}\n")

    response = requests.get(url, verify=False)
    soup = BeautifulSoup(response.content, "xml")
    
    # Cari bagian metadata
    meta = soup.find(['metadata', 'oai:metadata'])
    if not meta:
        print("[!] Data tidak ditemukan atau XML kosong.")
        return

    # Ambil semua teks yang ada di tag dc:description dan dc:subject
    desc_tags = meta.find_all(['description', 'dc:description'])
    subj_tags = meta.find_all(['subject', 'dc:subject'])
    
    print("--- DATA YANG DITEMUKAN DI XML ---")
    print(f"Description: {[t.text for t in desc_tags]}")
    print(f"Subject: {[t.text for t in subj_tags]}\n")

    # Jalankan logika mapping
    fac_map = {'FT': 'Teknik', 'FKIP': 'Keguruan', 'FMIPA': 'MIPA', 'FEB': 'Ekonomi'} # Contoh singkat
    
    all_text = " ".join([t.text.upper() for t in desc_tags + subj_tags])
    detected = next((full for short, full in fac_map.items() if short in all_text), "TIDAK TERDETEKSI")

    print("--- HASIL ANALISIS SCRIPT ---")
    print(f"Apakah Fakultas ketemu? {detected}")

# Masukkan angka ID dari screenshot kamu tadi (94610)
test_logic("94610")