import time
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import F, Q, Case, When, Value, FloatField, Count
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity
from django.core.cache import cache
from .models import DokumenAkademik, SearchTrend
from rest_framework import viewsets
from .serializers import DokumenSerializer

class DokumenViewSet(viewsets.ModelViewSet):
    queryset = DokumenAkademik.objects.all()
    serializer_class = DokumenSerializer

def index(request):
    # 🌟 PERBAIKAN UTAMA: Dibungkus dengan list() agar dieksekusi di dalam try-except
    try:
        top_trends = list(SearchTrend.objects.values('keyword').annotate(total=Count('keyword')).order_by('-total')[:5])
    except Exception:
        top_trends = []
        
    return render(request, 'index.html', {'top_trends': top_trends})

def search_view(request):
    start_time = time.time()

    query_text = request.GET.get('q', '').strip()
    page_number = request.GET.get('page', 1)
    
    source = request.GET.get('sumber', '').strip().lower()
    if not source:
        source = 'semua'
        
    min_year = request.GET.get('tahun_min', '')
    max_year = request.GET.get('tahun_max', '')
    faculty = request.GET.get('fakultas', '') 

    local_results = None
    total_found = 0
    total_digilib = 0
    total_lppm = 0
    execution_time = "0"

    if query_text:
        cache_version = cache.get('search_cache_version', 1)
        safe_query = query_text.replace(" ", "_")
        cache_key = f"search_{safe_query}_{source}_{faculty}_{min_year}_{max_year}_{page_number}_v{cache_version}"
        
        cached_html = cache.get(cache_key)
        
        if cached_html:
            try:
                SearchTrend.objects.create(keyword=query_text.lower()) 
            except Exception:
                pass
            return HttpResponse(cached_html)

        try:
            SearchTrend.objects.create(keyword=query_text.lower())
        except Exception:
            pass
        
        if source in ['semua', 'digilib', 'lppm']:
            base_query = SearchQuery(query_text, config='indonesian', search_type='websearch')
            phrase_query = SearchQuery(query_text, config='indonesian', search_type='phrase')
            
            base_filters = Q()
            if source == 'digilib':
                base_filters &= Q(source='DIGILIB')
            elif source == 'lppm':
                base_filters &= Q(source='LPPM')
                
            if faculty:
                base_filters &= Q(division__icontains=faculty)
            
            if min_year and min_year.isdigit():
                base_filters &= Q(year__gte=int(min_year))
            if max_year and max_year.isdigit():
                base_filters &= Q(year__lte=int(max_year))

            if " " in query_text.strip():
                queryset = DokumenAkademik.objects.filter(
                    base_filters,
                    search_vector=base_query
                ).annotate(
                    rank_base=SearchRank('search_vector', base_query),
                    rank_phrase=SearchRank('search_vector', phrase_query) * 10.0,
                    exact_score=Case(
                        When(title__icontains=query_text, then=Value(1000.0)),
                        When(author__icontains=query_text, then=Value(500.0)),
                        default=Value(0.0),
                        output_field=FloatField(),
                    )
                ).annotate(
                    total_rank=(F('exact_score') + F('rank_base') + F('rank_phrase'))
                ).order_by('-total_rank', '-year')
                
            else:
                queryset = DokumenAkademik.objects.filter(
                    base_filters,
                    search_vector=base_query
                ).annotate(
                    sim_title=TrigramSimilarity(Lower('title'), query_text.lower()),
                    sim_author=TrigramSimilarity(Lower('author'), query_text.lower()),
                    rank_base=SearchRank('search_vector', base_query),
                    exact_score=Case(
                        When(title__icontains=query_text, then=Value(1000.0)),
                        When(author__icontains=query_text, then=Value(500.0)),
                        default=Value(0.0),
                        output_field=FloatField(),
                    )
                ).annotate(
                    total_rank=(F('exact_score') + F('rank_base') + F('sim_title') + F('sim_author'))
                ).order_by('-total_rank', '-year')

            total_found = queryset.count()
            
            if total_found > 0:
                if source == 'semua':
                    total_digilib = queryset.filter(source='DIGILIB').count()
                    total_lppm = queryset.filter(source='LPPM').count()
                elif source == 'digilib':
                    total_digilib = total_found
                elif source == 'lppm':
                    total_lppm = total_found

            paginator = Paginator(queryset, 10)
            local_results = paginator.get_page(page_number)

    end_time = time.time()
    execution_time = str(round(end_time - start_time, 3)).replace('.', ',')

    context = {
        'page_obj': local_results,
        'query': query_text,
        'total_hasil': total_found,
        'total_digilib': total_digilib,
        'total_lppm': total_lppm,
        'sumber': source,
        'tahun_min': min_year,
        'tahun_max': max_year,
        'fakultas': faculty,
        'waktu_eksekusi': execution_time,
    }
    
    template_name = 'lppm_results.html' if source == 'lppm' else 'search_results.html'
    response = render(request, template_name, context)
    
    if query_text:
        cache.set(cache_key, response.content, timeout=2592000)

    return response

def detail_view(request, id):
    thesis = get_object_or_404(DokumenAkademik, id=id)
    return render(request, 'detail.html', {'skripsi': thesis})

def autocomplete_api(request):
    query = request.GET.get('q', '').strip()
    if len(query) > 2:
        suggestions = DokumenAkademik.objects.filter(title__icontains=query).values_list('title', flat=True)[:5]
        return JsonResponse(list(suggestions), safe=False)
    return JsonResponse([], safe=False)

def index(request):
    # Hitung jumlah berdasarkan field 'source'
    count_digilib = DokumenAkademik.objects.filter(source='DIGILIB').count()
    count_lppm = DokumenAkademik.objects.filter(source='LPPM').count()

    # Ambil tren
    try:
        top_trends = list(SearchTrend.objects.values('keyword').annotate(total=Count('keyword')).order_by('-total')[:5])
    except Exception:
        top_trends = []

    context = {
        'top_trends': top_trends,
        'jumlah_digilib': f"{count_digilib:,}".replace(',', '.'),
        'jumlah_lppm': f"{count_lppm:,}".replace(',', '.')
    }
    return render(request, 'index.html', context)