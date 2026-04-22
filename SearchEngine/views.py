from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .models import DokumenAkademik
from rest_framework import viewsets
from .serializers import DokumenSerializer

# --- 1. VIEWSET UNTUK API (Jika masih dibutuhkan untuk mobile/JS) ---
class DokumenViewSet(viewsets.ModelViewSet):
    queryset = DokumenAkademik.objects.all()
    serializer_class = DokumenSerializer

def index(request):
    return render(request, 'index.html')

# --- 2. VIEW UTAMA PENCARIAN (Untuk Halaman Web) ---
def search_view(request):
    """
    View ini menangani halaman depan (index.html) dan 
    halaman hasil pencarian (search_results.html).
    """
    # Mengambil parameter dari URL (input user)
    query_text = request.GET.get('q', '').strip()
    page_number = request.GET.get('page', 1)
    
    # Parameter tambahan dari template Rifdah agar tidak error
    sumber = request.GET.get('sumber', 'digilib')
    tahun_min = request.GET.get('tahun_min', '')
    tahun_max = request.GET.get('tahun_max', '')

    results = []
    total_found = 0

    if query_text:
        # Logika Full-Text Search PostgreSQL
        # Gunakan nama kolom asli kamu: title, abstract
        vector = SearchVector('title', weight='A') + SearchVector('abstract', weight='B')
        query = SearchQuery(query_text)
        
        # Eksekusi pencarian & Ranking
        queryset = DokumenAkademik.objects.annotate(
            rank=SearchRank(vector, query)
        ).filter(rank__gte=0.1).order_by('-rank')
        
        # Filter tambahan jika Rifdah mengirimkan filter tahun
        if tahun_min:
            queryset = queryset.filter(date_release__gte=tahun_min)
        if tahun_max:
            queryset = queryset.filter(date_release__lte=f"{tahun_max}-12-31")

        total_found = queryset.count()

        # Sistem Pagination: 10 hasil per halaman
        paginator = Paginator(queryset, 10)
        results = paginator.get_page(page_number)
    else:
        # Jika tidak ada keyword, tampilkan QuerySet kosong
        results = None

    # Context: Paket data yang dikirim ke HTML
    context = {
        'page_obj': results,        # Untuk looping di HTML
        'query': query_text,        # Menampilkan kembali kata kunci di search bar
        'total_hasil': total_found, # Total angka hasil pencarian
        'sumber': sumber,
        'tahun_min': tahun_min,
        'tahun_max': tahun_max,
    }
    
    # Jika ada keyword, tampilkan halaman hasil. Jika kosong, tampilkan Landing Page.
    if query_text:
        return render(request, 'search_results.html', context)
    return render(request, 'index.html', context)

# --- 3. VIEW UNTUK HALAMAN DETAIL ---
def detail_view(request, id):
    """
    Menampilkan detail lengkap satu dokumen berdasarkan ID.
    """
    # Mengambil satu data, jika tidak ada munculkan error 404
    skripsi = get_object_or_404(DokumenAkademik, id=id)
    
    return render(request, 'detail.html', {'skripsi': skripsi})