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
        # Menggabungkan semua (Publisher, Subject, Description)
        full_text = " ".join(filter(None, texts)).upper()
        
        # LOGIKA SUPER (Gabungan Keyword & Kode DDC Perpustakaan)
        if any(x in full_text for x in ['PENDIDIKAN', 'KEGURUAN', '370', 'FKIP', 'PGSD', 'PAUD']): 
            return 'Fakultas Keguruan dan Ilmu Pendidikan'
        if any(x in full_text for x in ['HUKUM', '340', 'FH']): 
            return 'Fakultas Hukum'
        if any(x in full_text for x in ['EKONOMI', 'AKUNTANSI', 'MANAJEMEN', 'BISNIS', 'PERBANKAN', 'PERPAJAKAN', '650', 'FEB']): 
            return 'Fakultas Ekonomi dan Bisnis'
        if any(x in full_text for x in ['TEKNIK', '620', 'SIPIL', 'MESIN', 'ELEKTRO', 'GEODESI', 'ARSITEKTUR', 'GEOFISIKA']): 
            return 'Fakultas Teknik'
        if any(x in full_text for x in ['PERTANIAN', '630', 'AGRONOMI', 'AGROTEKNOLOGI', 'KEHUTANAN', 'PETERNAKAN', 'FP', 'AGRIBISNIS']): 
            return 'Fakultas Pertanian'
        if any(x in full_text for x in ['KEDOKTERAN', '610', 'FARMASI', 'FK', 'KESEHATAN MASYARAKAT']): 
            return 'Fakultas Kedokteran'
        if any(x in full_text for x in ['SOSIAL', 'POLITIK', '300', 'KOMUNIKASI', 'SOSIOLOGI', 'FISIP', 'HUBUNGAN INTERNASIONAL', 'ADMINISTRASI NEGARA', 'PEMERINTAHAN']): 
            return 'Fakultas Ilmu Sosial dan Ilmu Politik'
        if any(x in full_text for x in ['MATEMATIKA', 'FISIKA', 'BIOLOGI', 'KIMIA', '500', '510', 'FMIPA', 'ILMU KOMPUTER', 'PENGETAHUAN ALAM']): 
            return 'Fakultas Matematika dan Ilmu Pengetahuan Alam'
        if any(x in full_text for x in ['PASCASARJANA', 'MAGISTER', 'DOKTOR']): 
            return 'Pascasarjana'
            
        return None

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Memulai proses FULL Ingest Data Digilib (Anti-Badai + Logika DDC Mode)..."))
        
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
                self.stdout.write(self.style.WARNING(f"\n[INFO] Menemukan titik henti! Melanjutkan dari token: {saved_token[:15]}...\n"))
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
                xml_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', xml_text)
                
                try:
                    root = ET.fromstring(xml_text.encode('utf-8'))
                except ET.ParseError as parse_err:
                    self.stdout.write(self.style.WARNING(f"\n[SKIP] XML Hancur ({parse_err}). Mencoba melompati..."))
                    token_match = re.search(r'<resumptionToken[^>]*>(.*?)</resumptionToken>', xml_text)
                    if token_match and token_match.group(1):
                        token = token_match.group(1)
                        with open(TOKEN_FILE, 'w') as f: f.write(token)
                        params = {'verb': 'ListRecords', 'resumptionToken': token}
                        self.stdout.write(self.style.SUCCESS(f"--- Token penyelamat ditemukan! Melompat... ---"))
                        time.sleep(2)
                        continue 
                    else:
                        break
                
                error = root.find('oai:error', namespaces)
                if error is not None:
                    self.stdout.write(self.style.ERROR(f"OAI Error: {error.text}"))
                    break

                records = root.findall('.//oai:record', namespaces)
                
                for record in records:
                    if total_processed >= 100:
                        break
                    total_processed += 1
                    header = record.find('oai:header', namespaces)
                    if header is not None and header.get('status') == 'deleted': continue
                    metadata = record.find('.//oai_dc:dc', namespaces)
                    if metadata is None: continue

                    # 1. IDENTIFIER
                    oai_id_raw = header.find('oai:identifier', namespaces).text
                    identifier_val = f"digilib_{oai_id_raw.split(':')[-1]}"

                    # 2. TITLE
                    title_elem = metadata.find('dc:title', namespaces)
                    title_val = title_elem.text if title_elem is not None else "Tanpa Judul"

                    # 3. AUTHOR
                    authors = [a.text for a in metadata.findall('dc:creator', namespaces) if a.text]
                    author_val = ", ".join(authors) if authors else None

                    # 4. ABSTRACT & DESCRIPTION
                    desc_elem = metadata.find('dc:description', namespaces)
                    abstract_val = desc_elem.text if desc_elem is not None else None

                    # 5. DATE
                    date_elem = metadata.find('dc:date', namespaces)
                    date_val, year_val = None, None
                    if date_elem is not None and date_elem.text:
                        date_str = date_elem.text.strip()
                        year_match = re.search(r'\d{4}', date_str)
                        if year_match: year_val = int(year_match.group())
                        try:
                            date_val = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                        except ValueError: pass 

                    # 6. DIVISION (FAKULTAS) - SEKARANG JAUH LEBIH PINTAR
                    # 6. DIVISION (FAKULTAS) & SUBJECT (JURUSAN)
                    publisher_elem = metadata.find('dc:publisher', namespaces)
                    subjects = metadata.findall('dc:subject', namespaces)
                    
                    # HANYA membaca Publisher dan Subject (DDC), JANGAN membaca Abstrak/Judul
                    texts_to_analyze = []
                    if publisher_elem is not None and publisher_elem.text: 
                        texts_to_analyze.append(publisher_elem.text)
                    texts_to_analyze.extend([s.text for s in subjects if s.text])
                            
                    division_val = self.get_full_division_name(texts_to_analyze)
                    if not division_val and publisher_elem is not None: 
                        division_val = publisher_elem.text.strip()

                    # 7. TYPE
                    types = [t.text for t in metadata.findall('dc:type', namespaces) if t.text and t.text.lower() not in ['text', 'nonpeerreviewed', 'peerreviewed']]
                    type_val = ", ".join(types) if types else "Dokumen"

                    # 8. URL
                    file_url_val, source_url_val = None, None
                    for ident in metadata.findall('dc:identifier', namespaces):
                        if ident.text:
                            url_text = ident.text.strip()
                            url_lower = url_text.lower()
                            if ('abstrak' in url_lower or 'abstrac' in url_lower) and url_lower.endswith('.pdf'): file_url_val = url_text
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
                            'type': type_val, 'division': division_val,
                            'file_url': file_url_val, 'source_url': source_url_val,
                            'synced_at': now()
                        }
                    )
                    if created: total_saved += 1
                    if total_processed % 10 == 0:
                        self.stdout.write(f"Scanning... ({total_processed} data dipindai, {total_saved} baru masuk DB)")

                if total_processed >= 100:
                    self.stdout.write(self.style.SUCCESS("\n[TEST MODE] Berhasil memproses 100 data uji coba. Proses dihentikan!"))
                    break
                
                # Paginasi & Simpan Token
                resumption_token = root.find('.//oai:resumptionToken', namespaces)
                if resumption_token is not None and resumption_token.text:
                    token = resumption_token.text
                    page_count += 1
                    self.stdout.write(self.style.SUCCESS(f"--- Selesai. Lanjut ke Halaman {page_count} ---"))
                    with open(TOKEN_FILE, 'w') as f: f.write(token)
                    params = {'verb': 'ListRecords', 'resumptionToken': token}
                    time.sleep(2) 
                else:
                    self.stdout.write(self.style.SUCCESS("\nSemua data di server Digilib sudah habis diproses!"))
                    if os.path.exists(TOKEN_FILE): os.remove(TOKEN_FILE)
                    break

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\nTerjadi kesalahan: {str(e)}. Jalankan ulang script untuk resume."))
                break
                
        self.stdout.write(self.style.SUCCESS(f"\nPROSES HARVEST SELESAI. Total dipindai: {total_processed} | Total baru: {total_saved}"))
        
        # ========================================================
        # UPDATE PEMBOBOTAN PENCARIAN (FTS) SANGAT CEPAT
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
        
        updated_count = DokumenAkademik.objects.filter(search_vector__isnull=True).update(search_vector=vector)
        duration = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"Selesai! {updated_count} data baru berhasil diindeks dalam {duration:.2f} detik. Sistem siap digunakan!"))