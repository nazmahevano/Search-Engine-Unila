import requests
import time
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from SearchEngine.models import DokumenAkademik

class Command(BaseCommand):
    help = 'Harvest ALL data from Unila Digilib using resumptionToken'

    def handle(self, *args, **kwargs):
        url = "http://digilib.unila.ac.id/cgi/oai2"
        
        # Inisialisasi awal
        params = {
            'verb': 'ListRecords',
            'metadataPrefix': 'oai_dc'
        }
        
        token = None
        page_count = 1

        self.stdout.write(self.style.HTTP_INFO("[*] Memulai Panen Raya Data Digilib Unila..."))

        while True:
            self.stdout.write(self.style.NOTICE(f"\n[*] Mengambil Halaman {page_count}..."))
            
            try:
                # Jika sudah ada token dari halaman sebelumnya, parameter berubah
                if token:
                    response = requests.get(url, params={'verb': 'ListRecords', 'resumptionToken': token}, timeout=60)
                else:
                    response = requests.get(url, params=params, timeout=60)

                soup = BeautifulSoup(response.content, "xml")
                records = soup.find_all(['record', 'oai:record'])

                if not records:
                    self.stdout.write(self.style.WARNING("[!] Tidak ada record ditemukan atau proses selesai."))
                    break

                # Proses simpan data (Logika sama seperti sebelumnya)
                for record in records:
                    meta = record.find(['metadata', 'oai:metadata'])
                    if not meta: continue

                    title = meta.find(['title', 'dc:title']).text if meta.find(['title', 'dc:title']) else "Tanpa title"
                    identifiers = meta.find_all(['identifier', 'dc:identifier'])
                    link = next((ids.text for ids in identifiers if ids.text.startswith('http://digilib.unila.ac.id/')), "")

                    if link:
                        # Ambil detail lain (Abstrak, Penulis, dll)
                        authors = ", ".join([c.text for c in meta.find_all(['creator', 'dc:creator'])])
                        date_issued = meta.find(['date', 'dc:date']).text.strip() if meta.find(['date', 'dc:date']) else ""
                        
                        descriptions = meta.find_all(['description', 'dc:description'])
                        abstract_text = max([d.text for d in descriptions], key=len) if descriptions else ""

                        # Update atau Buat Baru
                        DokumenAkademik.objects.update_or_create(
                            url_asli=link,
                            defaults={
                                'title': title,
                                'author': authors,
                                'source': 'digilib_unila',
                                'abstract': abstract_text,
                                'date_release': date_issued,
                            }
                        )

                self.stdout.write(self.style.SUCCESS(f"[OK] Halaman {page_count} selesai diproses."))

                # --- CEK APAKAH ADA HALAMAN BERIKUTNYA? ---
                res_token_tag = soup.find('resumptionToken')
                if res_token_tag and res_token_tag.text:
                    token = res_token_tag.text
                    page_count += 1
                    # Jeda 2 detik agar tidak dianggap menyerang server (Etika Crawler)
                    self.stdout.write(f"[*] Menunggu jeda server... (Token: {token[:15]}...)")
                    time.sleep(5) 
                else:
                    self.stdout.write(self.style.SUCCESS("\n[FINISH] Semua data sudah berhasil ditarik!"))
                    break

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[CRITICAL ERROR] Terhenti di halaman {page_count}: {str(e)}"))
                break