import time
from django.shortcuts import render, get_object_or_404
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity
from django.http import JsonResponse
from .models import DokumenAkademik
from rest_framework import viewsets
from .serializers import DokumenSerializer

class DokumenViewSet(viewsets.ModelViewSet):
    queryset = DokumenAkademik.objects.all()
    serializer_class = DokumenSerializer

def index(request):
    return render(request, 'index.html')

def search_view(request):
    start_time = time.time() # <-- WAKTU MULAI

    query_text = request.GET.get('q', '').strip()
    page_number = request.GET.get('page', 1)
    
    # Filter Tambahan
    sumber = request.GET.get('sumber', '').strip().lower()
    if not sumber:
        sumber = 'semua'
        
    tahun_min = request.GET.get('tahun_min', '')
    tahun_max = request.GET.get('tahun_max', '')
    fakultas = request.GET.get('fakultas', '') 

    results_lokal = None
    total_found = 0
    total_digilib = 0
    total_lppm = 0
    waktu_eksekusi = 0

    if query_text:
        if sumber in ['semua', 'digilib', 'lppm']:
            query = SearchQuery(query_text, config='indonesian')
            base_filters = Q()
            
            if sumber == 'digilib':
                base_filters &= Q(source='DIGILIB')
            elif sumber == 'lppm':
                base_filters &= Q(source='LPPM')
                
            if fakultas:
                base_filters &= Q(division__icontains=fakultas)
            
            if tahun_min and tahun_min.isdigit():
                base_filters &= Q(year__gte=int(tahun_min))
            if tahun_max and tahun_max.isdigit():
                base_filters &= Q(year__lte=int(tahun_max))

            # FTS & Fuzzy Search
            fts_base = DokumenAkademik.objects.filter(
                base_filters & (
                    Q(search_vector=query) | 
                    Q(author__icontains=query_text) | 
                    Q(title__icontains=query_text)
                )
            )

            # --- PERBAIKAN: MENGHITUNG ANGKA PASTI DARI DATABASE SEBELUM DILIMIT ---
            total_found = fts_base.count()
            
            if sumber == 'semua':
                total_digilib = fts_base.filter(source='DIGILIB').count()
                total_lppm = fts_base.filter(source='LPPM').count()
            elif sumber == 'digilib':
                total_digilib = total_found
                total_lppm = 0
            elif sumber == 'lppm':
                total_digilib = 0
                total_lppm = total_found
            # ----------------------------------------------------------------------

            # Baru potong/limit hasilnya setelah dihitung
            fts_ids = list(fts_base.values_list('id', flat=True)[:3000])
            
            fuzzy_base = DokumenAkademik.objects.annotate(
                sim_title=TrigramSimilarity(Lower('title'), query_text.lower()),
                sim_author=TrigramSimilarity(Lower('author'), query_text.lower())
            ).filter(
                base_filters, 
                Q(sim_title__gt=0.2) | Q(sim_author__gt=0.2) 
            )
            
            fuzzy_ids = list(
                fuzzy_base.annotate(total_sim=F('sim_title') + F('sim_author'))
                          .order_by('-total_sim')
                          .values_list('id', flat=True)[:1000]
            )

            all_ids = list(set(fts_ids + fuzzy_ids))

            queryset = DokumenAkademik.objects.filter(id__in=all_ids).annotate(
                rank=SearchRank('search_vector', query, weights=[0.05, 0.1, 0.1, 1.0], normalization=2),
                similarity=TrigramSimilarity(Lower('title'), query_text.lower())
            ).annotate(
                total_rank=(F('rank') + F('similarity'))
            ).order_by('-total_rank', '-year')
            
            paginator = Paginator(queryset, 10)
            results_lokal = paginator.get_page(page_number)

    end_time = time.time() # <-- WAKTU SELESAI
    waktu_eksekusi = str(round(end_time - start_time, 3)).replace('.', ',') 

    context = {
        'page_obj': results_lokal,
        'query': query_text,
        'total_hasil': total_found,
        'total_digilib': total_digilib,
        'total_lppm': total_lppm,
        'sumber': sumber,
        'tahun_min': tahun_min,
        'tahun_max': tahun_max,
        'fakultas': fakultas,
        'waktu_eksekusi': waktu_eksekusi, 
    }
    
    if sumber == 'lppm':
        template = 'lppm_results.html'
    else:
        template = 'search_results.html'
        
    return render(request, template, context)

def detail_view(request, id):
    skripsi = get_object_or_404(DokumenAkademik, id=id)
    return render(request, 'detail.html', {'skripsi': skripsi})

def autocomplete_api(request):
    query = request.GET.get('q', '').strip()
    # Mulai cari saran jika pengguna sudah mengetik lebih dari 2 huruf
    if len(query) > 2:
        # Mengambil 5 judul skripsi yang mengandung kata yang diketik
        saran = DokumenAkademik.objects.filter(title__icontains=query).values_list('title', flat=True)[:5]
        return JsonResponse(list(saran), safe=False)
    return JsonResponse([], safe=False)