import time
import random
from scholarly import scholarly
from django.core.management.base import BaseCommand
from SearchEngine.models import DokumenAkademik

class Command(BaseCommand):
    help = 'Harvest Unila research data using scholarly library with filtering'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.HTTP_INFO("[*] Starting Scholarly Harvest for Universitas Lampung..."))
        
        try:
            # 1. Cari author dengan keyword Universitas Lampung
            # Kita gunakan generator untuk menghemat memori
            search_query = scholarly.search_author('Universitas Lampung')
            
            author_count = 0
            # Batasi jumlah author agar tidak cepat kena banned (Contoh: 5 author)
            max_authors = 5 

            for author_info in search_query:
                if author_count >= max_authors:
                    break
                
                name = author_info.get('name')
                email = author_info.get('email_domain', '')
                
                self.stdout.write(f"\n[*] Checking Author: {name} (Domain: {email})")

                # --- FILTER DOMAIN EMAIL UNILA ---
                if 'unila.ac.id' in email.lower():
                    self.stdout.write(self.style.SUCCESS(f"    [MATCH] Verified Unila Author found!"))
                    
                    # 2. Ambil profil lengkap termasuk daftar publikasi
                    self.stdout.write(f"    [!] Fetching publications for {name}...")
                    author = scholarly.fill(author_info)
                    publications = author.get('publications', [])
                    
                    self.stdout.write(f"    [+] Found {len(publications)} publications. Ingesting top 10...")

                    # 3. Looping untuk simpan publikasi (ambil 10 teratas saja per orang)
                    for pub in publications[:10]:
                        title = pub.get('bib', {}).get('title', 'No Title')
                        pub_id = pub.get('author_pub_id', '')
                        
                        # Generate URL unik dari ID publikasi Google Scholar
                        url_scholar = f"https://scholar.google.com/citations?view_op=view_citation&citation_for_view={pub_id}"

                        # Simpan ke Database
                        obj, created = DokumenAkademik.objects.get_or_create(
                            url_asli=url_scholar,
                            defaults={
                                'title': title,
                                'author': name,
                                'source': 'scholar',
                                'abstract': f"Verified Unila Publication by {name}"
                            }
                        )

                        if created:
                            self.stdout.write(f"        [SAVED] {title[:60]}...")
                        else:
                            self.stdout.write(self.style.WARNING(f"        [SKIP] Already exists: {title[:60]}..."))
                    
                    author_count += 1
                    
                    # Kasih jeda random agar terlihat seperti manusia (3-7 detik)
                    wait_time = random.randint(3, 7)
                    self.stdout.write(f"[*] Sleeping for {wait_time}s to avoid bot detection...")
                    time.sleep(wait_time)
                else:
                    self.stdout.write(self.style.WARNING(f"    [SKIP] External Institution: {name}"))

            self.stdout.write(self.style.SUCCESS(f"\n[DONE] Successfully processed {author_count} verified authors."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[CRITICAL ERROR] {str(e)}"))
            self.stdout.write(self.style.WARNING("Tips: Jika error '429 Too Many Requests', ganti koneksi ke Hotspot HP sekarang!"))