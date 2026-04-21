import requests
import time
import urllib3
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from SearchEngine.models import DokumenAkademik

# Matikan peringatan SSL agar terminal tetap bersih
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Command(BaseCommand):
    help = 'Patching Final: Membersihkan data fakultas yang kosong menggunakan logika Subject & DDC'

    def handle(self, *args, **kwargs):
        # Konfigurasi Endpoint
        url = "https://digilib.unila.ac.id/cgi/oai2"
        params = {'verb': 'ListRecords', 'metadataPrefix': 'oai_dc'}
        token = None
        page_count = 1
        total_patched = 0
        total_skipped = 0

        self.stdout.write(self.style.HTTP_INFO(f"[*] MEMULAI PROSES MEMBERSIHKAN DATA (PATCHING)..."))

        while True:
            self.stdout.write(self.style.NOTICE(f"\n[>] Menyisir Halaman {page_count}..."))
            
            try:
                # Request ke server (dengan resumptionToken jika ada)
                request_params = {'verb': 'ListRecords', 'resumptionToken': token} if token else params
                response = requests.get(url, params=request_params, timeout=60, verify=False)
                
                soup = BeautifulSoup(response.content, "xml")
                records = soup.find_all(['record', 'oai:record'])

                if not records:
                    self.stdout.write("[!] Selesai: Tidak ada data lagi.")
                    break

                for record in records:
                    header = record.find(['header', 'oai:header'])
                    oai_id = header.find(['identifier', 'oai:identifier']).text if header else None
                    
                    if not oai_id:
                        continue
                    
                    # 1. Cari data di Supabase berdasarkan Identifier (KTP Data)
                    doc = DokumenAkademik.objects.filter(identifier=oai_id).first()

                    # 2. LOGIKA PATCHING: Hanya proses jika data ada DAN fakultasnya masih kosong/NULL
                    if doc and (not doc.faculty or doc.faculty in ["None", "", "NULL"]):
                        meta = record.find(['metadata', 'oai:metadata'])
                        if not meta: continue

                        # Ambil data dari berbagai tag untuk deteksi fakultas
                        subjects = [t.text.upper() for t in meta.find_all(['subject', 'dc:subject'])]
                        publisher = meta.find(['publisher', 'dc:publisher']).text.upper() if meta.find(['publisher', 'dc:publisher']) else ""
                        description = meta.find(['description', 'dc:description']).text.upper() if meta.find(['description', 'dc:description']) else ""
                        
                        # Gabungkan semua untuk dicek sekaligus
                        full_text = " ".join(subjects) + " " + publisher + " " + description

                        # --- SISTEM PRIORITAS MAPPING (Gunakan Keyword & Kode DDC) ---
                        
                        # Prioritas 1: FKIP (Cek Pendidikan/Keguruan dulu agar tidak tertukar FMIPA)
                        if any(x in full_text for x in ['PENDIDIKAN', 'KEGURUAN', '370', 'FKIP']):
                            doc.faculty = 'Fakultas Keguruan dan Ilmu Pendidikan'
                        
                        # Prioritas 2: HUKUM
                        elif any(x in full_text for x in ['HUKUM', '340', 'FH']):
                            doc.faculty = 'Fakultas Hukum'
                        
                        # Prioritas 3: FEB (Ekonomi, Akuntansi, Manajemen)
                        elif any(x in full_text for x in ['EKONOMI', 'AKUNTANSI', 'MANAJEMEN', '650', 'FEB']):
                            doc.faculty = 'Fakultas Ekonomi dan Bisnis'
                        
                        # Prioritas 4: TEKNIK (Sipil, Mesin, Elektro, Geodesi)
                        elif any(x in full_text for x in ['TEKNIK', '620', 'SIPIL', 'MESIN', 'ELEKTRO', 'GEODESI', 'ARSITEKTUR']):
                            doc.faculty = 'Fakultas Teknik'
                        
                        # Prioritas 5: PERTANIAN (Agronomi, Kehutanan, Peternakan)
                        elif any(x in full_text for x in ['PERTANIAN', '630', 'AGRONOMI', 'KEHUTANAN', 'PETERNAKAN', 'FP']):
                            doc.faculty = 'Fakultas Pertanian'
                        
                        # Prioritas 6: KEDOKTERAN (Farmasi, Profesi Dokter)
                        elif any(x in full_text for x in ['KEDOKTERAN', '610', 'FARMASI', 'FK']):
                            doc.faculty = 'Fakultas Kedokteran'
                        
                        # Prioritas 7: FISIP (Sosial, Politik, Komunikasi, Sosiologi)
                        elif any(x in full_text for x in ['SOSIAL', 'POLITIK', '300', 'KOMUNIKASI', 'SOSIOLOGI', 'FISIP']):
                            doc.faculty = 'Fakultas Ilmu Sosial dan Ilmu Politik'
                        
                        # Prioritas 8: FMIPA (Matematika, Fisika, Biologi, Kimia, Ilmu Komputer)
                        elif any(x in full_text for x in ['MATEMATIKA', 'FISIKA', 'BIOLOGI', 'KIMIA', '500', '510', 'FMIPA', 'ILMU KOMPUTER']):
                            # Double check: Jika sudah lolos dari filter Pendidikan (FKIP)
                            doc.faculty = 'Fakultas Matematika dan Ilmu Pengetahuan Alam'

                        # Jika berhasil terdeteksi, simpan perubahannya
                        if doc.faculty:
                            doc.save()
                            total_patched += 1
                            self.stdout.write(f"   [FIXED] {doc.title[:45]}... -> {doc.faculty}")
                    else:
                        # Jika sudah ada isinya atau data tidak ketemu, lewati
                        total_skipped += 1

                self.stdout.write(self.style.SUCCESS(f"[OK] Halaman {page_count} Selesai diproses."))

                # --- Ambil Resumption Token ---
                res_token_tag = soup.find('resumptionToken')
                if res_token_tag and res_token_tag.text:
                    token = res_token_tag.text
                    page_count += 1
                    time.sleep(0.5) # Jeda singkat biar ngebut tapi aman
                else:
                    break

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[ERROR] Masalah di Halaman {page_count}: {str(e)}"))
                break

        self.stdout.write(self.style.SUCCESS(f"\n[FINISH] Proses Patching Selesai!"))
        self.stdout.write(f"Total Baris Diperbaiki: {total_patched}")
        self.stdout.write(f"Total Baris Dilewati: {total_skipped}")