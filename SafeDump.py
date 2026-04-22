import os
import json
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UnilaSearch.settings') # Pastikan 'core' sesuai nama folder setting kamu
django.setup()

from SearchEngine.models import DokumenAkademik

def run_dump():
    print("[*] Memulai proses export 58k data...")
    all_data = []
    
    # Kita tarik datanya per 1000 biar gak error cursor
    queryset = DokumenAkademik.objects.all().iterator(chunk_size=1000)
    
    count = 0
    for obj in queryset:
        # Format data agar sesuai standar loaddata Django
        data_item = {
            "model": "SearchEngine.dokumenakademik",
            "pk": obj.pk,
            "fields": {
                "title": obj.title,
                "author": obj.author,
                "abstract": obj.abstract,
                "faculty": obj.faculty,
                "type": obj.type,
                "date_release": str(obj.date_release) if obj.date_release else None,
                "url_asli": obj.url_asli,
                "source": obj.source,
            }
        }
        all_data.append(data_item)
        count += 1
        if count % 1000 == 0:
            print(f"[+] Berhasil memproses {count} data...")

    # Simpan ke file JSON
    with open('data_58k.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=4)
    
    print(f"\n[DONE] Selesai! {count} data aman di 'data_58k.json'")

if __name__ == "__main__":
    run_dump()