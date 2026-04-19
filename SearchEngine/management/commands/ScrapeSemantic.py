import requests
import time
from django.core.management.base import BaseCommand
from SearchEngine.models import DokumenAkademik

class Command(BaseCommand):
    help = 'Harvest and verify Unila research data from Semantic Scholar API'

    def handle(self, *args, **kwargs):
        # 1. Konfigurasi API
        # Kita minta field 'authors.affiliations' untuk verifikasi instansi
        query = "Universitas Lampung"
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': query,
            'limit': 50, # Kita ambil 50 sampel untuk di-filter
            'fields': 'title,authors.name,authors.affiliations,abstract,url,year'
        }

        self.stdout.write(self.style.HTTP_INFO(f"[*] Connecting to Semantic Scholar..."))
        self.stdout.write(f"[*] Target: Papers with verified 'Universitas Lampung' affiliation.\n")

        try:
            response = requests.get(url, params=params, timeout=20)
            
            if response.status_code == 200:
                papers = response.json().get('data', [])
                self.stdout.write(f"[*] Found {len(papers)} potential matches. Starting verification...")

                count_saved = 0
                for paper in papers:
                    title = paper.get('title', 'No Title')
                    authors_data = paper.get('authors', [])
                    
                    # --- LOGIKA SATPAM: FILTER AFILIASI ---
                    is_verified_unila = False
                    author_names_list = []

                    for author in authors_data:
                        name = author.get('name', 'Unknown Author')
                        author_names_list.append(name)
                        
                        # Cek setiap afiliasi yang dimiliki penulis ini
                        affiliations = author.get('affiliations', [])
                        for aff in affiliations:
                            if "universitas lampung" in aff.lower():
                                is_verified_unila = True
                                break # Satu penulis Unila saja sudah cukup untuk verifikasi paper ini
                    
                    # --- EKSEKUSI HASIL FILTER ---
                    if not is_verified_unila:
                        # Jika tidak ada satupun penulis dari Unila, jangan masukkan ke database
                        self.stdout.write(self.style.WARNING(f"   [SKIP] Non-Unila Affiliation: {title[:50]}..."))
                        continue

                    # Jika lolos (Verified Unila), simpan ke PostgreSQL
                    authors_str = ", ".join(author_names_list)
                    paper_url = paper.get('url') or f"https://www.semanticscholar.org/paper/{paper.get('paperId')}"
                    abstract = paper.get('abstract') or "No abstract available"
                    
                    obj, created = DokumenAkademik.objects.get_or_create(
                        url_asli=paper_url,
                        defaults={
                            'title': title,
                            'author': authors_str,
                            'source': 'semantic_scholar',
                            'abstract': abstract[:1000] # Batasi agar tidak meledakkan database
                        }
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f"   [VERIFIED] Saved: {title[:60]}..."))
                        count_saved += 1
                    else:
                        self.stdout.write(self.style.NOTICE(f"   [EXIST] Already in DB: {title[:60]}..."))
                
                self.stdout.write(self.style.SUCCESS(f"\n[DONE] Successfully verified and saved {count_saved} papers."))

            elif response.status_code == 429:
                self.stdout.write(self.style.ERROR("[!] Error 429: Too Many Requests. API Semantic Scholar lagi sibuk, coba lagi 5 menit lagi."))
            else:
                self.stdout.write(self.style.ERROR(f"[!] API Error: {response.status_code}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[CRITICAL ERROR] {str(e)}"))