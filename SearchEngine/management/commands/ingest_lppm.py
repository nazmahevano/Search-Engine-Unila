import time
import requests
import re
from xml.etree import ElementTree as ET
from django.core.management.base import BaseCommand
from SearchEngine.models import DokumenAkademik
from django.utils.timezone import now
from django.db import models

class Command(BaseCommand):
    help = 'Harvest data FULL dari LPPM Unila via OAI-PMH (Revisi Final: Filter Relation URL Eksternal)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Memulai proses FULL Ingest Data LPPM... (Pastikan koneksi internet stabil)"))
        
        base_url = 'http://repository.lppm.unila.ac.id/cgi/oai2'
        
        namespaces = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }

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
                    self.stdout.write(self.style.WARNING(f"Server LPPM sibuk (503). Menunggu {retry_after} detik..."))
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                root = ET.fromstring(response.content)
                
                error = root.find('oai:error', namespaces)
                if error is not None:
                    self.stdout.write(self.style.ERROR(f"OAI Error: {error.text}"))
                    break

                records = root.findall('.//oai:record', namespaces)
                
                for record in records:
                    total_processed += 1

                    header = record.find('oai:header', namespaces)
                    if header is not None and header.get('status') == 'deleted':
                        continue

                    metadata = record.find('.//oai_dc:dc', namespaces)
                    if metadata is None:
                        continue

                    # 1. IDENTIFIER & ORIGINAL ID
                    oai_id_raw = header.find('oai:identifier', namespaces).text
                    original_id = oai_id_raw.split(':')[-1]
                    identifier_val = f"lppm_{original_id}"

                    # 2. TITLE
                    title_elem = metadata.find('dc:title', namespaces)
                    title_val = title_elem.text if title_elem is not None else "Tanpa Judul"

                    # 3. AUTHOR
                    authors = [a.text for a in metadata.findall('dc:creator', namespaces) if a.text]
                    author_val = ", ".join(authors) if authors else None

                    # 4. ABSTRACT
                    desc_elem = metadata.find('dc:description', namespaces)
                    abstract_val = desc_elem.text if desc_elem is not None else None

                    # 5. YEAR (date_release dikosongkan)
                    date_elem = metadata.find('dc:date', namespaces)
                    year_val = None
                    if date_elem is not None and date_elem.text:
                        year_match = re.search(r'\d{4}', date_elem.text)
                        if year_match: 
                            year_val = int(year_match.group())

                    # 6. TYPE 
                    types = []
                    for t in metadata.findall('dc:type', namespaces):
                        if t.text:
                            t_lower = t.text.lower()
                            if t_lower not in ['text', 'nonpeerreviewed', 'peerreviewed']:
                                types.append(t.text)
                    type_val = ", ".join(types) if types else "Dokumen LPPM"

                    # 7. FILE URL (Hanya mencari ekstensi .pdf)
                    file_url_val = None
                    identifiers = metadata.findall('dc:identifier', namespaces)
                    for ident in identifiers:
                        if ident.text and ident.text.lower().endswith('.pdf'):
                            if not file_url_val: 
                                file_url_val = ident.text.strip()
                    
                    # 8. SOURCE URL (Format paten)
                    source_url_val = f"http://repository.lppm.unila.ac.id/{original_id}/"

                    # 9. RELATION (Hanya mengambil link eksternal)
                    relations = []
                    for rel in metadata.findall('dc:relation', namespaces):
                        if rel.text and rel.text.startswith('http'):
                            # Abaikan jika link tersebut adalah link repository LPPM
                            if 'repository.lppm.unila.ac.id' not in rel.text.lower():
                                relations.append(rel.text.strip())
                                
                    relation_val = "\n".join(relations) if relations else None

                    # === SIMPAN KE DATABASE ===
                    obj, created = DokumenAkademik.objects.update_or_create(
                        identifier=identifier_val,
                        defaults={
                            'title': title_val,
                            'author': author_val,
                            'abstract': abstract_val,
                            'date_release': None,       
                            'year': year_val,
                            'source': 'LPPM',
                            'access': 'public',
                            'type': type_val,
                            'division': None,           
                            'subject': None, 
                            'relation': relation_val,   
                            'file_url': file_url_val,
                            'source_url': source_url_val, 
                            'synced_at': now()
                        }
                    )
                    
                    if created:
                        total_saved += 1
                        
                    # LOG TERMINAL: Muncul setiap memproses kelipatan 100
                    if total_processed % 100 == 0:
                        self.stdout.write(f"Sedang membaca sistem LPPM... ({total_processed} data dipindai, {total_saved} baru masuk DB)")


                # Paginasi (Pindah Halaman)
                resumption_token = root.find('.//oai:resumptionToken', namespaces)
                if resumption_token is not None and resumption_token.text:
                    token = resumption_token.text
                    page_count += 1
                    self.stdout.write(self.style.SUCCESS(f"--- Selesai Halaman {page_count-1}. Lanjut Halaman {page_count} (Token: {token}) ---"))
                    params = {'verb': 'ListRecords', 'resumptionToken': token}
                    time.sleep(2)  # Jeda 2 detik yang sopan
                else:
                    self.stdout.write(self.style.SUCCESS("\nTidak ada token halaman lagi. Semua data di server LPPM sudah habis diproses!"))
                    break

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\nTerjadi kesalahan jaringan atau sistem: {str(e)}"))
                self.stdout.write(self.style.WARNING("Jika proses terhenti, jalankan ulang script ini. Data yang sudah tersimpan tidak akan terduplikasi."))
                break
                
        self.stdout.write(self.style.SUCCESS(f"\nPROSES HARVEST LPPM SELESAI. Total dipindai: {total_processed} | Total baru tersimpan: {total_saved}"))
        
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