from django.shortcuts import render, get_object_or_404
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity
from django.http import JsonResponse
from .models import DokumenAkademik
from .services import SemanticScholarService
from rest_framework import viewsets
from .serializers import DokumenSerializer

class DokumenViewSet(viewsets.ModelViewSet):
    queryset = DokumenAkademik.objects.all()
    serializer_class = DokumenSerializer

def index(request):
    return render(request, 'index.html')

def search_view(request):
    query_text = request.GET.get('q', '').strip()
    page_number = request.GET.get('page', 1)
    
    # Filter Tambahan (Sudah aman dari typo)
    sumber = request.GET.get('sumber', 'semua').strip().lower()
    if not sumber:
        sumber = 'semua'
    tahun_min = request.GET.get('tahun_min', '')
    tahun_max = request.GET.get('tahun_max', '')
    fakultas = request.GET.get('fakultas', '') 

    results_lokal = None
    total_found = 0

    if query_text:
        if sumber in ['semua', 'digilib', 'lppm']:
            query = SearchQuery(query_text, config='indonesian')
            base_filters = Q(access='public')
            
            if sumber == 'digilib':
                base_filters &= Q(source='DIGILIB')
            elif sumber == 'lppm':
                base_filters &= Q(source='LPPM')
                
            if fakultas:
                base_filters &= Q(division__icontains=fakultas)
            
            # --- PERBAIKAN TAHUN (Diubah jadi Integer) ---
            if tahun_min and tahun_min.isdigit():
                base_filters &= Q(year__gte=int(tahun_min))
            if tahun_max and tahun_max.isdigit():
                base_filters &= Q(year__lte=int(tahun_max))

            # --- PERBAIKAN LIMIT & TAMBAHAN PENCARIAN PENULIS ---
            fts_base = DokumenAkademik.objects.filter(
                base_filters & (
                    Q(search_vector=query) | 
                    Q(author__icontains=query_text) | 
                    Q(title__icontains=query_text)
                )
            )
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
            total_found = len(all_ids)

            queryset = DokumenAkademik.objects.filter(id__in=all_ids).annotate(
                rank=SearchRank('search_vector', query, weights=[0.05, 0.1, 0.1, 1.0], normalization=2),
                similarity=TrigramSimilarity(Lower('title'), query_text.lower())
            ).annotate(
                total_rank=(F('rank') + F('similarity'))
            ).order_by('-total_rank', '-year')
            
            paginator = Paginator(queryset, 10)
            results_lokal = paginator.get_page(page_number)

    context = {
        'page_obj': results_lokal,
        'query': query_text,
        'total_hasil': f"{total_found}+" if total_found >= 3000 else total_found,
        'sumber': sumber,
        'tahun_min': tahun_min,
        'tahun_max': tahun_max,
        'fakultas': fakultas,
    }
    
    # --- PERBAIKAN: JALUR TEMPLATE 3 CABANG ---
    if sumber == 'scholar':
        template = 'semantic_results.html'
    elif sumber == 'lppm':
        template = 'lppm_results.html'
    else:
        template = 'search_results.html'
        
    return render(request, template, context)

def search_global_api(request):
    query_text = request.GET.get('q', '').strip()
    if not query_text:
        return JsonResponse({'results': []})
    results = SemanticScholarService.search_papers(query_text)
    return JsonResponse({'results': results})

def detail_view(request, id):
    skripsi = get_object_or_404(DokumenAkademik, id=id)
    return render(request, 'detail.html', {'skripsi': skripsi})