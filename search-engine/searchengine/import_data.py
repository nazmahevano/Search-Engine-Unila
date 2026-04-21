import os
import django
import csv

# 1. Konfigurasi agar script ini bisa menggunakan fitur Database Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'searchengine.settings')
django.setup()

# Import model kamu SETELAH django.setup()
from app.models import Digilib

def jalankan_import():
    # Ganti 'data_skripsi.csv' dengan nama file kamu yang sebenarnya
    file_path = 'data_skripsi.csv' 
    
    print("Mulai membaca file CSV...")
    
    # Buka file CSV
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        
        # Jika file kamu punya baris pertama sebagai Header (Judul Kolom), aktifkan baris di bawah ini:
        # next(reader) 
        
        jumlah_sukses = 0
        
        for row in reader:
            try:
                # --- SESUAIKAN URUTAN KOLOM (INDEX) DENGAN FILE CSV KAMU ---
                # Berdasarkan gambar, kolomnya kira-kira seperti ini:
                # row[0] = ID (1, 2, 3...)
                # row[1] = Judul ("Praktik Manajemen CSR...")
                # row[2] = Penulis ("Wildan, Abdurrahman...")
                # row[... dan seterusnya]
                
                judul_data = row[1].strip() if len(row) > 1 else "Tanpa Judul"
                penulis_data = row[2].strip() if len(row) > 2 else "Anonim"
                
                # Masukkan ke dalam Database Digilib
                Digilib.objects.create(
                    judul=judul_data,
                    penulis=penulis_data,
                    tahun=2024, # Isi default jika di CSV tidak ada tahun yang spesifik
                    abstrak="Abstrak belum tersedia dari sumber data.", # Isi default
                    # Jika ada URL/Link di CSV kamu, masukkan ke tautan_file
                )
                jumlah_sukses += 1
                
            except Exception as e:
                print(f"Gagal memproses baris: {row}. Error: {e}")
                
    print(f"Selesai! Berhasil memasukkan {jumlah_sukses} data ke database Digilib.")

if __name__ == '__main__':
    jalankan_import()