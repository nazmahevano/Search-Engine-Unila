import os
import time
import requests
import re
from xml.etree import ElementTree as ET
from django.core.management.base import BaseCommand
from SearchEngine.models import DokumenAkademik
from django.utils.timezone import now
from django.db import models

class Command(BaseCommand):
    help = 'Ingesting metadata from LPPM Universitas Lampung via OAI-PMH'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Starting FULL Ingest Data LPPM via OAI-PMH"))
        
        base_url = 'http://repository.lppm.unila.ac.id/cgi/oai2'
        TOKEN_FILE = 'lppm_resume_token.txt'
        
        namespaces = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }

        # LOGIKA AUTO-RESUME
        params = {}
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                saved_token = f.read().strip()
            
            if saved_token:
                self.stdout.write(self.style.WARNING(f"\n[NOTE] Found resume point! Continuing from token: {saved_token[:15]}...\n"))
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
                headers = {'User-Agent': 'SearchEngineUnila-Machine/1.0 (Skripsi Project)'}
                response = requests.get(base_url, params=params, headers=headers, timeout=60)
                
                if response.status_code == 503:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.stdout.write(self.style.WARNING(f"Error connection time out (503). Waiting {retry_after} seconds..."))
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                xml_text = response.text
                xml_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', xml_text)
                
                try:
                    root = ET.fromstring(xml_text.encode('utf-8'))
                except ET.ParseError as parse_err:
                    self.stdout.write(self.style.WARNING(f"\n[SKIP] XML crash ({parse_err}). Try to next..."))
                    token_match = re.search(r'<resumptionToken[^>]*>(.*?)</resumptionToken>', xml_text)
                    if token_match and token_match.group(1):
                        token = token_match.group(1)
                        with open(TOKEN_FILE, 'w') as f: f.write(token)
                        params = {'verb': 'ListRecords', 'resumptionToken': token}
                        self.stdout.write(self.style.SUCCESS(f"Token was founded! Next..."))
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
                    total_processed += 1

                    header = record.find('oai:header', namespaces)
                    if header is not None and header.get('status') == 'deleted':
                        continue

                    metadata = record.find('.//oai_dc:dc', namespaces)
                    if metadata is None:
                        continue

                    # 1. IDENTIFIER
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

                    # 5. YEAR
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

                    # 7. FILE URL
                    file_url_val = None
                    identifiers = metadata.findall('dc:identifier', namespaces)
                    for ident in identifiers:
                        if ident.text and ident.text.lower().endswith('.pdf'):
                            if not file_url_val: 
                                file_url_val = ident.text.strip()
                    
                    # 8. SOURCE URL
                    source_url_val = f"http://repository.lppm.unila.ac.id/{original_id}/"

                    # 9. RELATION (URL eksternal)
                    relations = []
                    for rel in metadata.findall('dc:relation', namespaces):
                        if rel.text and rel.text.startswith('http'):
                            if 'repository.lppm.unila.ac.id' not in rel.text.lower():
                                relations.append(rel.text.strip())
                                
                    relation_val = "\n".join(relations) if relations else None

                    # SIMPAN KE DATABASE
                    obj, created = DokumenAkademik.objects.update_or_create(
                        identifier=identifier_val,
                        defaults={
                            'title': title_val,
                            'author': author_val,
                            'abstract': abstract_val,
                            'date_release': None,       
                            'year': year_val,
                            'source': 'LPPM',
                            'type': type_val,
                            'division': None,           
                            'relation': relation_val,   
                            'file_url': file_url_val,
                            'source_url': source_url_val, 
                            'synced_at': now()
                        }
                    )
                    
                    if created:
                        total_saved += 1
                        
                    if total_processed % 100 == 0:
                        self.stdout.write(f"Scanning... ({total_processed} scanned data, {total_saved} just entered database)")

                # Paginasi & Simpan Token
                resumption_token = root.find('.//oai:resumptionToken', namespaces)
                if resumption_token is not None and resumption_token.text:
                    token = resumption_token.text
                    page_count += 1
                    self.stdout.write(self.style.SUCCESS(f"--- Finished {page_count-1}. Continuing to Page {page_count} ---"))

                    with open(TOKEN_FILE, 'w') as f: 
                        f.write(token)
                        
                    params = {'verb': 'ListRecords', 'resumptionToken': token}
                    time.sleep(2)  
                else:
                    self.stdout.write(self.style.SUCCESS("\nAll data in LPPM server has been processed!"))
                    if os.path.exists(TOKEN_FILE): 
                        os.remove(TOKEN_FILE)
                    break

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\nTerjadi kesalahan jaringan atau sistem: {str(e)}"))
                self.stdout.write(self.style.WARNING("Just run the script again, it will automatically continue from the last page."))
                break
                
        self.stdout.write(self.style.SUCCESS(f"\nProcess Harvest finished. Total scanned: {total_processed} | Total new entries: {total_saved}"))

        # PEMBOBOTAN PENCARIAN (FTS)
        self.stdout.write(self.style.WARNING("\nStarting process update search index (FTS)..."))
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
        self.stdout.write(self.style.SUCCESS(f"Finished! {updated_count} new data successfully indexed in {duration:.2f} seconds. System is ready for use!"))