from django.db import models
from django.shortcuts import render, get_object_or_404
from django.db.models.functions import Lower
from django.db.models import F, Q
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.http import JsonResponse
from .models import DokumenAkademik
from .services import SemanticScholarService
from rest_framework import viewsets
from .serializers import DokumenSerializer

from SearchEngine import models
from django.contrib.postgres.search import TrigramSimilarity

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
    fakultas = request.GET.get('fakultas', '') # TAMBAHAN: Ambil data fakultas dari URL

    results_lokal = None
    total_found = 0

    if query_text:
        # --- A. PROSES DIGILIB UNILA (LOKAL) ---
        # Kita cuma proses lokal di sini biar loading halaman secepat kilat!
        if sumber in ['semua', 'digilib']:
            # --- TAHAP 1: CARI ID (AKURAT & TYPO) ---
            # 1. Ambil ID yang kena FTS (Akurat)
            query = SearchQuery(query_text, config='indonesian', search_type='websearch')
            fts_ids = list(DokumenAkademik.objects.filter(search_vector=query)
                           .annotate(rank=SearchRank('search_vector', query))
                           .order_by('-rank')
                           .values_list('id', flat=True)[:500])
            
            base_queryset = DokumenAkademik.objects.filter(search_vector=query)
            if tahun_min:
                base_queryset = base_queryset.filter(date_release__gte=tahun_min)
            if tahun_max:
                base_queryset = base_queryset.filter(date_release__lte=f"{tahun_max}-12-31")
            
            # TAMBAHAN: Lakukan filter ke kolom 'faculty' di database
            if fakultas: 
                base_queryset = base_queryset.filter(faculty__icontains=fakultas)
            # 2. Ambil ID yang kena Trigram (Fuzzy/Typo) - Kita pake saringan 0.1 biar anlaisa ketemu
            fuzzy_ids = list(DokumenAkademik.objects.annotate(
                sim=TrigramSimilarity(Lower('title'), query_text.lower())
            ).filter(sim__gt=0.1)
            .order_by('-sim') # <-- INI KUNCINYA: Biar Analisa ngalahin yang lain
            .values_list('id', flat=True)[:500])

            # Gabungkan semua ID, buang yang duplikat
            all_ids = list(set(fts_ids + fuzzy_ids))
            total_found = len(all_ids)

            # 3. Proses Ranking dan Scoring
            queryset = DokumenAkademik.objects.filter(id__in=all_ids).annotate(
                # Skor FTS buat yang ngetiknya bener
                fts_rank=SearchRank(
                    'search_vector', 
                    query, 
                    weights=[0.05, 0.1, 0.1, 1.0],
                    normalization=2
                ),
                # Skor Similarity buat yang typo
                fuzzy_score=TrigramSimilarity('title', query_text)
            ).annotate(
                # Gabungin skornya
                total_rank=(F('fts_rank') + F('fuzzy_score'))
            ).order_by('-total_rank', '-date_release')

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
        'fakultas': fakultas, # TAMBAHAN: Jangan lupa kirim ke template agar pilihan tidak hilang
        # 'global_results' sengaja gak diisi di sini biar gak nungguin API
    }
    if sumber == 'scholar':
        return render(request, 'semantic_results.html', context)
    else:
        return render(request, 'search_results.html', context)

# --- 3. JALUR KHUSUS DATA GLOBAL (JSON UNTUK RIFDAH) ---
def search_global_api(request):
    """
    Endpoint ini cuma balikin data mentah (JSON).
    Rifdah bakal manggil ini pake JavaScript (AJAX).
    """
    query_text = request.GET.get('q', '').strip()
    t_min = request.GET.get('tahun_min', '')
    t_max = request.GET.get('tahun_max', '')
    
    if not query_text:
        return JsonResponse({'results': []})
        
    # Panggil service (sudah ada Cache & Backoff di services.py lo)
    results = SemanticScholarService.search_papers(
        query=query_text,
        year=f"{t_min}-{t_max}" if t_min and t_max else None
    )
    
    # Balikin data ke Rifdah
    return JsonResponse({'results': results})

# --- 4. DETAIL VIEW ---
def detail_view(request, id):
    skripsi = get_object_or_404(DokumenAkademik, id=id)
    return render(request, 'detail.html', {'skripsi': skripsi})