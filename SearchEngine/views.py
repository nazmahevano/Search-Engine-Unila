from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.http import JsonResponse
from .models import DokumenAkademik
from .services import SemanticScholarService
from rest_framework import viewsets
from .serializers import DokumenSerializer


class DokumenViewSet(viewsets.ModelViewSet):
    queryset = DokumenAkademik.objects.all()
    serializer_class = DokumenSerializer
    
# --- 1. HALAMAN UTAMA ---
def index(request):
    return render(request, 'index.html')

# --- 2. VIEW UTAMA PENCARIAN (KHUSUS LOKAL/UNILA) ---
def search_view(request):
    """
    View ini fokus nampilin hasil dari database lokal (Digilib Unila).
    Hasil global dikosongkan karena akan dipanggil lewat AJAX oleh Rifdah.
    """
    query_text = request.GET.get('q', '').strip()
    page_number = request.GET.get('page', 1)
    
    # Parameter filter
    sumber = request.GET.get('sumber', 'semua')
    tahun_min = request.GET.get('tahun_min', '')
    tahun_max = request.GET.get('tahun_max', '')

    results_lokal = None
    total_found = 0

    if query_text:
        # --- A. PROSES DIGILIB UNILA (LOKAL) ---
        # Kita cuma proses lokal di sini biar loading halaman secepat kilat!
        if sumber in ['semua', 'digilib']:
            query = SearchQuery(query_text, config='indonesian')
            
            base_queryset = DokumenAkademik.objects.filter(search_vector=query)
            if tahun_min:
                base_queryset = base_queryset.filter(date_release__gte=tahun_min)
            if tahun_max:
                base_queryset = base_queryset.filter(date_release__lte=f"{tahun_max}-12-31")

            matched_ids = base_queryset.order_by('-date_release').values_list('id', flat=True)[:1000]
            
            queryset = DokumenAkademik.objects.filter(
                id__in=matched_ids
            ).annotate(
                rank=SearchRank(
                    'search_vector', 
                    query, 
                    weights=[0.05, 0.1, 0.1, 1.0],
                    normalization=2 
                )
            ).order_by('-rank', '-date_release')
            
            total_found = len(matched_ids)
            paginator = Paginator(queryset, 10)
            results_lokal = paginator.get_page(page_number)

    # Context untuk dikirim ke template
    context = {
        'page_obj': results_lokal,
        'query': query_text,
        'total_hasil': f"{total_found}+" if total_found >= 1000 else total_found,
        'sumber': sumber,
        'tahun_min': tahun_min,
        'tahun_max': tahun_max,
        # 'global_results' sengaja gak diisi di sini biar gak nungguin API
    }
    return render(request, 'search_results.html', context)

# --- 3. JALUR KHUSUS DATA GLOBAL (JSON UNTUK RIFDAH) ---
def search_global_api(request):
    """
    Endpoint ini cuma balikin data mentah (JSON).
    Rifdah bakal manggil ini pake JavaScript (AJAX).
    """
    query_text = request.GET.get('q', '').strip()
    
    if not query_text:
        return JsonResponse({'results': []})
        
    # Panggil service (sudah ada Cache & Backoff di services.py lo)
    results = SemanticScholarService.search_papers(query_text)
    
    # Balikin data ke Rifdah
    return JsonResponse({'results': results})

# --- 4. DETAIL VIEW ---
def detail_view(request, id):
    skripsi = get_object_or_404(DokumenAkademik, id=id)
    return render(request, 'detail.html', {'skripsi': skripsi})