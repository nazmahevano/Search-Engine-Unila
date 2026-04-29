import os
import time
import requests
import re
from xml.etree import ElementTree as ET
from datetime import datetime
from django.core.management.base import BaseCommand
from SearchEngine.models import DokumenAkademik
from django.utils.timezone import now
from django.db import models

class Command(BaseCommand):
    help = 'Harvest data FULL dari Digilib Unila via OAI-PMH (Anti-Badai XML Rusak & Auto-Resume)'

    def get_full_division_name(self, texts):
        combined_text = " ".join(filter(None, texts)).upper()
        if any(keyword in combined_text for keyword in ['FEB', 'EKONOMI', 'BISNIS', 'AKUNTANSI', 'MANAJEMEN', 'PERBANKAN', 'PERPAJAKAN', 'HD']): return 'Fakultas Ekonomi dan Bisnis'
        if any(keyword in combined_text for keyword in ['FISIP', 'SOSIAL', 'POLITIK', 'KOMUNIKASI', 'HUBUNGAN INTERNASIONAL', 'ADMINISTRASI NEGARA', 'PEMERINTAHAN', 'SOSIOLOGI']): return 'Fakultas Ilmu Sosial dan Ilmu Politik'
        if any(keyword in combined_text for keyword in ['FKIP', 'KEGURUAN', 'PENDIDIKAN', 'PGSD', 'PAUD', 'BIMBINGAN DAN KONSELING']): return 'Fakultas Keguruan dan Ilmu Pendidikan'
        if any(keyword in combined_text for keyword in ['FMIPA', 'MIPA', 'MATEMATIKA', 'PENGETAHUAN ALAM', 'ILMU KOMPUTER', 'BIOLOGI', 'KIMIA', 'FISIKA']): return 'Fakultas Matematika dan Ilmu Pengetahuan Alam'
        if any(keyword in combined_text for keyword in ['FK', 'KEDOKTERAN', 'FARMASI', 'KESEHATAN MASYARAKAT']): return 'Fakultas Kedokteran'
        if any(keyword in combined_text for keyword in ['FP', 'PERTANIAN', 'AGRIBISNIS', 'AGRONOMI', 'AGROTEKNOLOGI', 'KEHUTANAN', 'PETERNAKAN']): return 'Fakultas Pertanian'
        if any(keyword in combined_text for keyword in ['FT', 'TEKNIK', 'SIPIL', 'MESIN', 'ARSITEKTUR', 'GEOFISIKA', 'GEODESI']): return 'Fakultas Teknik'
        if any(keyword in combined_text for keyword in ['FH', 'HUKUM']): return 'Fakultas Hukum'
        if 'PASCASARJANA' in combined_text or 'MAGISTER' in combined_text or 'DOKTOR' in combined_text: return 'Pascasarjana'
        return None

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Memulai proses FULL Ingest Data Digilib (Anti-Badai Mode)..."))
        
        base_url = 'http://digilib.unila.ac.id/cgi/oai2'
        TOKEN_FILE = 'digilib_resume_token.txt' 
        
        namespaces = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }

        # --- LOGIKA AUTO-RESUME ---
        params = {}
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                saved_token = f.read().strip()
            
            if saved_token:
                self.stdout.write(self.style.WARNING(f"\n[INFO] Menemukan titik henti sebelumnya! Melanjutkan langsung dari token: {saved_token}\n"))
                params = {'verb': 'ListRecords', 'resumptionToken': saved_token}
            else:
                params = {'verb': 'ListRecords', 'metadataPrefix': 'oai_dc'}
        else:
            params = {'verb': 'ListRecords', 'metadataPrefix': 'oai_dc'}
        
        total_saved = 0
        total_processed = 0
        page_count = 1
        
        while True:
            try:
                headers = {'User-Agent': 'SearchEngineUnila-Bot/1.0 (Skripsi Project)'}
                response = requests.get(base_url, params=params, headers=headers, timeout=60) 
                
                if response.status_code == 503:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.stdout.write(self.style.WARNING(f"Server Unila sibuk (503). Menunggu {retry_after} detik..."))
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                # --- PERTAHANAN ANTI-BADAI XML ---
                xml_text = response.text
                # 1. Sapu bersih karakter siluman / invalid control characters
                xml_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', xml_text)
                
                try:
                    root = ET.fromstring(xml_text.encode('utf-8'))
                except ET.ParseError as parse_err:
                    self.stdout.write(self.style.WARNING(f"\n[SKIP] Format XML Digilib hancur di halaman ini ({parse_err}). Mencoba melompati..."))
                    
                    # 2. Paksa ambil token untuk melompat menggunakan Regex
                    token_match = re.search(r'<resumptionToken[^>]*>(.*?)</resumptionToken>', xml_text)
                    if token_match and token_match.group(1):
                        token = token_match.group(1)
                        with open(TOKEN_FILE, 'w') as f:
                            f.write(token)
                        params = {'verb': 'ListRecords', 'resumptionToken': token}
                        self.stdout.write(self.style.SUCCESS(f"--- Token penyelamat ditemukan! Melompat ke halaman berikutnya... ---"))
                        time.sleep(2)
                        continue # Lompati iterasi ini, langsung lanjut narik data berikutnya
                    else:
                        self.stdout.write(self.style.ERROR("XML terlalu hancur dan tidak ada token penyelamat. Proses benar-benar berhenti."))
                        break
                # ----------------------------------
                
                error = root.find('oai:error', namespaces)
                if error is not None:
                    self.stdout.write(self.style.ERROR(f"OAI Error: {error.text}"))
                    break

                records = root.findall('.//oai:record', namespaces)
                
                for record in records:
                    total_processed += 1

                    header = record.find('oai:header', namespaces)
                    if header is not None and header.get('status') == 'deleted': continue

                    metadata = record.find('.//oai_dc:dc', namespaces)
                    if metadata is None: continue

                    # 1. IDENTIFIER
                    oai_id_raw = header.find('oai:identifier', namespaces).text
                    original_id = oai_id_raw.split(':')[-1]
                    identifier_val = f"digilib_{original_id}"

                    # 2. TITLE
                    title_elem = metadata.find('dc:title', namespaces)
                    title_val = title_elem.text if title_elem is not None else "Tanpa Judul"

                    # 3. AUTHOR
                    authors = [a.text for a in metadata.findall('dc:creator', namespaces) if a.text]
                    author_val = ", ".join(authors) if authors else None

                    # 4. ABSTRACT
                    desc_elem = metadata.find('dc:description', namespaces)
                    abstract_val = desc_elem.text if desc_elem is not None else None

                    # 5. DATE & YEAR
                    date_elem = metadata.find('dc:date', namespaces)
                    date_val = None
                    year_val = None
                    if date_elem is not None and date_elem.text:
                        date_str = date_elem.text.strip()
                        year_match = re.search(r'\d{4}', date_str)
                        if year_match: year_val = int(year_match.group())
                        try:
                            date_val = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                        except ValueError: pass 

                    # 6. DIVISION
                    publisher_elem = metadata.find('dc:publisher', namespaces)
                    subjects = metadata.findall('dc:subject', namespaces)
                    texts_to_analyze = [publisher_elem.text] if publisher_elem is not None and publisher_elem.text else []
                    texts_to_analyze.extend([s.text for s in subjects if s.text])
                            
                    division_val = self.get_full_division_name(texts_to_analyze)
                    if not division_val and publisher_elem is not None: division_val = publisher_elem.text.strip()

                    # 7. TYPE
                    types = [t.text for t in metadata.findall('dc:type', namespaces) if t.text and t.text.lower() not in ['text', 'nonpeerreviewed', 'peerreviewed']]
                    type_val = ", ".join(types) if types else "Dokumen"

                    # 8. URL
                    file_url_val = None
                    source_url_val = None
                    
                    identifiers = metadata.findall('dc:identifier', namespaces)
                    for ident in identifiers:
                        if ident.text:
                            url_text = ident.text.strip()
                            url_lower = url_text.lower()
                            
                            if ('abstrak' in url_lower or 'abstrac' in url_lower) and url_lower.endswith('.pdf'):
                                file_url_val = url_text
                            elif url_text.startswith('http') and not url_lower.endswith('.pdf'):
                                if not source_url_val: source_url_val = url_text
                    
                    relation_elem = metadata.find('dc:relation', namespaces)
                    if relation_elem is not None and relation_elem.text and relation_elem.text.startswith('http'):
                        source_url_val = relation_elem.text

                    # === SIMPAN KE DATABASE ===
                    obj, created = DokumenAkademik.objects.update_or_create(
                        identifier=identifier_val,
                        defaults={
                            'title': title_val, 'author': author_val, 'abstract': abstract_val,
                            'date_release': date_val, 'year': year_val, 'source': 'DIGILIB',
                            'access': 'public', 'type': type_val, 'division': division_val,
                            'subject': None, 'file_url': file_url_val, 'source_url': source_url_val,
                            'synced_at': now()
                        }
                    )
                    if created: total_saved += 1
                    
                    if total_processed % 100 == 0:
                        self.stdout.write(f"Sedang membaca sistem... ({total_processed} data dipindai, {total_saved} baru masuk DB)")

                # Paginasi & Simpan Token
                resumption_token = root.find('.//oai:resumptionToken', namespaces)
                if resumption_token is not None and resumption_token.text:
                    token = resumption_token.text
                    page_count += 1
                    self.stdout.write(self.style.SUCCESS(f"--- Selesai. Menyimpan Token: {token} & Lanjut Halaman Berikutnya ---"))
                    
                    with open(TOKEN_FILE, 'w') as f: f.write(token)
                    params = {'verb': 'ListRecords', 'resumptionToken': token}
                    time.sleep(2) 
                else:
                    self.stdout.write(self.style.SUCCESS("\nSemua data di server Digilib sudah habis diproses!"))
                    if os.path.exists(TOKEN_FILE): os.remove(TOKEN_FILE)
                    break

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\nTerjadi kesalahan jaringan/sistem: {str(e)}"))
                self.stdout.write(self.style.WARNING("Tinggal jalankan ulang script ini, nanti akan langsung lanjut dari halaman terakhir."))
                break
                
        self.stdout.write(self.style.SUCCESS(f"\nPROSES HARVEST SELESAI. Total dipindai sesi ini: {total_processed} | Total baru: {total_saved}"))
        
        # ========================================================
        # TAMBAHAN BARU: OTOMATIS UPDATE PEMBOBOTAN PENCARIAN
        # ========================================================
        self.stdout.write(self.style.WARNING("\nMemulai proses update indeks pencarian (FTS)..."))
        from django.contrib.postgres.search import SearchVector
        from django.db.models import Value
        from django.db.models.functions import Coalesce
        
        start_time = time.time()
        vector = (
            SearchVector(Coalesce('title', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='A', config='indonesian') +
            SearchVector(Coalesce('author', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='B', config='indonesian') +
            SearchVector(Coalesce('abstract', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='C', config='indonesian')
        )
        
        # Opsi Pintar: Hanya perbarui data yang search_vector-nya masih kosong (data baru)
        # agar prosesnya secepat kilat!
        updated_count = DokumenAkademik.objects.filter(search_vector__isnull=True).update(search_vector=vector)
        
        duration = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"Selesai! {updated_count} data baru berhasil diindeks dalam {duration:.2f} detik. Sistem siap digunakan!"))