import os
import django
import time

# 1. Setup supaya file ini bisa akses database Django kamu
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UnilaSearch.settings') # Sesuaikan nama folder settingsmu
django.setup()

from SearchEngine.models import DokumenAkademik
from django.db import connection

# 2. Pengaturan Batch
batch_size = 100 # Kita naikin dikit biar cepet
total_data = DokumenAkademik.objects.count()
processed = 37400

print(f"🚀 Memulai update bobot untuk {total_data} data...")
print("Jangan tutup terminal ini sampai selesai ya!")

while processed < total_data:
    # Ambil ID batch berikutnya
    ids = list(DokumenAkademik.objects.all().order_by('id').values_list('id', flat=True)[processed : processed + batch_size])
    
    if not ids:
        break

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = 0")
            # SQL sakti untuk kasih label A (Judul) dan B (Abstrak)
            cursor.execute(f"""
                UPDATE "SearchEngine_dokumenakademik"
                SET search_vector = 
                    setweight(to_tsvector('indonesian', coalesce(title, '')), 'A') || 
                    setweight(to_tsvector('indonesian', coalesce(abstract, '')), 'B')
                WHERE id IN %s
            """, [tuple(ids)])
        
        processed += len(ids)
        print(f"✅ Berhasil: {processed}/{total_data} data...")
        
    except Exception as e:
        print(f"❌ Error di batch ini: {e}")
        time.sleep(2) # Kalau error, istirahat bentar terus lanjut

    time.sleep(0.5)

print("\n🎉 SELESAI! Database kamu sekarang sudah punya kasta cerdas.")