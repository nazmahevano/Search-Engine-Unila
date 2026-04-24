import os
import requests
import time
from pathlib import Path
from dotenv import load_dotenv
from django.core.cache import cache # Penjaga gudang memori

# Load .env biar API Key kebaca
base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / '.env'
load_dotenv(dotenv_path=env_path)

class SemanticScholarService:
    @staticmethod
    def search_papers(query_text, limit=10):
        if not query_text:
            return []

        # 1. CEK GUDANG (Cache)
        # Bikin kunci unik berdasarkan kata kunci pencarian
        cache_key = f"semantic_{query_text.replace(' ', '_').lower()}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            print(f"🚀 CACHE HIT: Ambil data '{query_text}' dari memori (Gak nembak API)")
            return cached_data

        # 2. JIKA GAK ADA DI GUDANG, BARU TEMBAK API
        api_key = os.getenv("SEMANTIC_API_KEY")
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        headers = {'x-api-key': api_key} if api_key else {}
        
        # Sesuai dokumentasi: Mengunci hasil agar hanya dari Universitas Lampung
        final_query = f'{query_text} "Universitas Lampung"'

        params = {
            'query': final_query,
            'limit': limit,
            'fields': 'title,authors,year,url,abstract,venue'
        }

        try:
            # Jeda 1.5 detik (Aturan resmi: max 1 request/detik)
            time.sleep(1.5) 
            print(f"📡 API CALL: Mencari '{query_text}' ke Semantic Scholar...")
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json().get('data', [])
                # SIMPEN KE GUDANG (Cache) selama 1 jam
                cache.set(cache_key, data, 3600)
                return data
            
            print(f"⚠️ API Error {response.status_code}: {response.text}")
            return []
            
        except Exception as e:
            print(f"❌ Error Koneksi: {e}")
            return []

# --- BAGIAN TESTING MANDIRI ---
if __name__ == "__main__":
    # Karena kita pake Django Cache, bagian ini mungkin error kalau 
    # dijalankan via 'python services.py' tanpa env Django. 
    # Jadi tesnya langsung via 'runserver' aja ya Naz!
    pass