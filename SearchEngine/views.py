from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .models import DokumenAkademik

def api_search(request):
    # 1. Ambil kata kunci dari user (misal: ?q=kecerdasan buatan)
    query_text = request.GET.get('q', '')
    
    if query_text:
        # 2. Logika Search PostgreSQL (Mencari di Judul dan Abstrak)
        vector = SearchVector('judul', weight='A') + SearchVector('abstrak', weight='B')
        query = SearchQuery(query_text)
        
        # 3. Eksekusi pencarian & urutkan berdasarkan yang paling relevan
        results = DokumenAkademik.objects.annotate(
            rank=SearchRank(vector, query)
        ).filter(rank__gte=0.1).order_by('-rank')[:20] # Ambil 20 teratas dulu
        
        # 4. Format data jadi JSON
        data = []
        for item in results:
            data.append({
                'judul': item.judul,
                'penulis': item.penulis,
                'abstrak': item.abstrak[:200] + "...", # Potong biar gak kepanjangan
                'url': item.url_asli,
                'skor': round(item.rank, 2)
            })
            
        return JsonResponse({'status': 'success', 'total': len(data), 'results': data})
    
    return JsonResponse({'status': 'error', 'message': 'Mana keyword-nya?'}, status=400)