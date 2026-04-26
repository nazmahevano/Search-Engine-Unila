import requests
import time
from django.conf import settings
from django.core.cache import cache # Penjaga gudang memori

class SemanticScholarService:
    @staticmethod
    def search_papers(query_text, limit=10):
        if not query_text:
            return []

        # 1. CEK GUDANG (Cache)
        cache_key = f"semantic_{query_text.replace(' ', '_').lower()}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            print(f"🚀 CACHE HIT: Ambil data '{query_text}' dari memori (Gak nembak API)")
            return cached_data

        # 2. JIKA GAK ADA DI GUDANG, BARU TEMBAK API
        api_key = getattr(settings, 'SEMANTIC_SCHOLAR_API_KEY', None)
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        headers = {'x-api-key': api_key} if api_key else {}
        
        # === DIKEMBALIKAN SEPERTI SEMULA ===
        # Mengunci hasil agar hanya dari Universitas Lampung
        final_query = f'{query_text} "Universitas Lampung"'

        params = {
            'query': final_query,
            'limit': limit,
            'fields': 'title,authors,year,url,abstract,venue'
        }

        try:
            # Jika tidak pakai API Key, baru disuruh antre lambat
            if not api_key:
                time.sleep(1.5) 
                
            print(f"📡 API CALL: Mencari '{query_text}' (Khusus Unila) ke Semantic Scholar...")
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json().get('data', [])
                # SIMPEN KE GUDANG (Cache) selama 1 jam
                cache.set(cache_key, data, 3600)
                return data
            
            print(f"⚠️ API Error {response.status_code}: {response.text}")
            return []
            
        except Exception as e:
            print(f"❌ Error Koneksi API: {e}")
            return []

# --- BAGIAN TESTING MANDIRI ---
if __name__ == "__main__":
    pass