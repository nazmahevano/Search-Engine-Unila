from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Digilib

# Create your views here.
def index(request):
    return render(request, 'index.html')

def search(request):
    query = request.GET.get('q', '')
    tahun_min = request.GET.get('tahun_min', '')
    tahun_max = request.GET.get('tahun_max', '')
    # fakultas = request.GET.get('fakultas', '') # KITA MATIKAN KARENA TIDAK ADA DI DB
    
    # Ambil sumber database tunggal (default: all)
    sumber = request.GET.get('sumber', 'all') 

    hasil_digilib = []
    hasil_eksternal = []

    # --- 1. LOGIKA DIGILIB ---
    if sumber in ['digilib', 'all']:
        # Ambil SEMUA data mentah dari awal (Trik agar muncul semua)
        qs = Digilib.objects.all()
        
        # Jika pengguna memasukkan kata kunci/filter, baru data disaring
        if query:
            qs = qs.filter(Q(judul__icontains=query) | Q(penulis__icontains=query) | Q(abstrak__icontains=query))
        
        # PERUBAHAN: Ganti 'tahun' menjadi 'tanggal_terbit'
        if tahun_min: qs = qs.filter(tanggal_terbit__gte=tahun_min)
        if tahun_max: qs = qs.filter(tanggal_terbit__lte=tahun_max)
        
        # Filter fakultas dihapus dari sini agar tidak error
        
        hasil_digilib = qs

    # --- 2. LOGIKA SCHOLAR ---
    if sumber in ['scholar', 'all']:
        # Khusus Scholar WAJIB memiliki query, jika kosong API akan error
        if query: 
            url_api = f"https://api.openalex.org/works?search={query}&per-page=5"
            api_filters = []
            if tahun_min: api_filters.append(f"from_publication_date:{tahun_min}-01-01")
            if tahun_max: api_filters.append(f"to_publication_date:{tahun_max}-12-31")
            if api_filters: url_api += "&filter=" + ",".join(api_filters)

            try:
                response = request.get(url_api) # PERUBAHAN: Pakai 'requests.get' (ada huruf s)
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get('results', []):
                        penulis = item['authorships'][0]['author']['display_name'] if item.get('authorships') else "Anonim"
                        hasil_eksternal.append({
                            'judul': item.get('title', 'Tanpa Judul'),
                            'penulis': penulis,
                            # PERUBAHAN: Ganti nama kunci 'tahun' jadi 'tanggal_terbit' agar cocok dengan HTML
                            'tanggal_terbit': item.get('publication_year', '-'),
                            'link': item.get('doi', '#')
                        })
            except Exception as e:
                print("Error API Scholar:", e) # Agar kalau error, terlihat di terminal
    
    # 1. Gabungkan semua hasil ke dalam satu list
    hasil_gabungan = list(hasil_digilib[:100]) + list(hasil_eksternal)
    
    # 2. Atur Paginator (Misal: 10 data per halaman)
    paginator = Paginator(hasil_gabungan, 10)
    
    # 3. Ambil nomor halaman dari URL (misal: ?page=2)
    page_number = request.GET.get('page')
    
    # 4. Ambil objek data untuk halaman tersebut
    page_obj = paginator.get_page(page_number)

    context = {
        'query': query,
        'tahun_min': tahun_min,
        'tahun_max': tahun_max,
        # 'fakultas': fakultas, -> Dihapus dari context
        'sumber': sumber,
        'hasil_digilib': hasil_digilib,
        'hasil_eksternal': hasil_eksternal,
        'total_hasil': len(hasil_gabungan),
        'page_obj': page_obj,
    }
    return render(request, 'search_results.html', context)

# --- 3. LOGIKA HALAMAN DETAIL ---
def detail(request, id):
    # Mengambil data Digilib berdasarkan ID, jika tidak ada, munculkan error 404
    skripsi = get_object_or_404(Digilib, id=id)
    
    # Kirim data satu skripsi ini ke file template HTML
    return render(request, 'detail.html', {'skripsi': skripsi})