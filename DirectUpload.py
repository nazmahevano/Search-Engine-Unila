import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UnilaSearchDigilib.settings') 
django.setup()

from SearchEngine.models import DokumenAkademik

def pindah_data():
    print("[*] Menyiapkan tabel di Supabase...")
    # Pastikan tabel di Supabase sudah ada (migrate dulu sebelum jalankan ini)
    
    # Ambil data dari database 'lokal'
    print("[*] Mulai menarik data dari local dan kirim ke Supabase...")
    data_local = DokumenAkademik.objects.using('local').all()
    
    total = data_local.count()
    print(f"[*] Total data yang akan dipindah: {total}")

    batch_size = 100
    count = 0
    
    for obj in data_local:
        # Kita hapus ID-nya biar Supabase yang buat ID baru secara otomatis (lebih aman)
        obj.pk = None 
        # Simpan ke database default (Supabase)
        obj.save(using='default')
        
        count += 1
        if count % 100 == 0:
            print(f"[+] Berhasil upload {count} dari {total} data...")

    print("\n[DONE] Semua data sudah terbang ke Supabase!")

if __name__ == "__main__":
    pindah_data()