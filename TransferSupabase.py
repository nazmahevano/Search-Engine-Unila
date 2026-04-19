import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UnilaSearch.settings') 
django.setup()

from SearchEngine.models import DokumenAkademik

def mulai_transfer_turbo():
    print("[*] Menghubungkan ke database local...")
    data_local = DokumenAkademik.objects.using('local').all()
    total = data_local.count()
    
    print(f"[*] Total: {total} data. Memulai Turbo Upload (Skip Data Ganda)...")

    batch_size = 500
    batch_list = []
    count = 0

    for item in data_local:
        new_item = DokumenAkademik(
            title=item.title,
            author=item.author,
            abstract=item.abstract,
            # fakulty=item.fakulty, # Pakai kalau ada di models.py
            # major=item.major,       # Pakai kalau ada di models.py
            date_release=item.date_release,
            url_asli=item.url_asli,
            source=item.source
        )
        batch_list.append(new_item)
        
        if len(batch_list) >= batch_size:
            # KUNCI RAHASIANYA DI SINI: ignore_conflicts=True
            DokumenAkademik.objects.using('default').bulk_create(batch_list, ignore_conflicts=True)
            count += len(batch_list)
            print(f"[TURBO] Memproses {count} data...")
            batch_list = []

    if batch_list:
        DokumenAkademik.objects.using('default').bulk_create(batch_list, ignore_conflicts=True)
        print(f"[FINISH] Berhasil cek/upload semua {total} data.")

if __name__ == "__main__":
    mulai_transfer_turbo()