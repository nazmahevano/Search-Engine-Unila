import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .models import DokumenAkademik
from rest_framework import viewsets
from .serializers import DokumenSerializer

class DokumenViewSet(viewsets.ModelViewSet):
    queryset = DokumenAkademik.objects.all() # Ambil semua skripsi
    serializer_class = DokumenSerializer

def api_search(request):
    # 1. Ambil kata kunci dari user
    query_text = request.GET.get('q', '')
    
    if query_text:
        # 2. Logika Search PostgreSQL (Mencari di Judul dan Abstrak)
        # Kita pakai SearchVector dan SearchRank agar hasilnya paling relevan ada di atas
        vector = SearchVector('title', weight='A') + SearchVector('abstract', weight='B')
        query = SearchQuery(query_text)
        
        # 3. Eksekusi pencarian di database lokal (Digilib)
        results = DokumenAkademik.objects.annotate(
            rank=SearchRank(vector, query)
        ).filter(rank__gte=0.1).order_by('-rank')[:20] # Kita ambil 20 data terbaik
        
        # 4. Format data lokal jadi JSON
        data_lokal = []
        for item in results:
            data_lokal.append({
                'title': item.title,
                'author': item.author,
                # Pastikan abstract gak null dan dipotong biar hemat bandwidth
                'abstract': (item.abstract or "")[:300] + "...", 
                'url': item.url_digilib,
                'source': 'Digilib Unila',
                'year': str(item.date_release)[:4] if item.date_release else "N/A",
                'skor': round(item.rank, 2)
            })
            
        return JsonResponse({
            'status': 'success', 
            'total_found': len(data_lokal), 
            'results': data_lokal
        })
    
    return JsonResponse({'status': 'error', 'message': 'Masukkan kata kunci pencarian'}, status=400)