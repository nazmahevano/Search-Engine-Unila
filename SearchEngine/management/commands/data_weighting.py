import time
from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector
from django.db.models import Value
from django.db.models.functions import Coalesce
from SearchEngine.models import DokumenAkademik
from django.db import models

class Command(BaseCommand):
    help = 'Update search_vector secara bertahap (Anti-Timeout)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Mulai memperbarui search_vector (Mode Bertahap Anti-Timeout)..."))
        
        start_time = time.time()
        
        # Pembobotan: A (Sangat Penting), B (Penting), C (Standar)
        vector = (
            SearchVector(Coalesce('title', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='A', config='indonesian') +
            SearchVector(Coalesce('author', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='B', config='indonesian') +
            SearchVector(Coalesce('abstract', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='C', config='indonesian')
        )
        
        # 1. Mendata semua ID dokumen yang ada (TIDAK bikin data baru)
        self.stdout.write("Mendata seluruh dokumen, mohon tunggu sebentar...")
        all_ids = list(DokumenAkademik.objects.values_list('id', flat=True))
        total_data = len(all_ids)
        
        # 2. Atur ukuran suapan (2.000 data per proses)
        chunk_size = 2000 
        processed = 0

        self.stdout.write(self.style.WARNING(f"Total ada {total_data} data. Memulai pemrosesan per {chunk_size} data..."))

        # 3. Looping update sepotong-sepotong agar Supabase tidak ngambek
        for i in range(0, total_data, chunk_size):
            batch_ids = all_ids[i:i + chunk_size]
            
            # Update khusus untuk batch ini saja
            DokumenAkademik.objects.filter(id__in=batch_ids).update(search_vector=vector)
            
            processed += len(batch_ids)
            self.stdout.write(f"-> Berhasil memproses: {processed} / {total_data} data...")
        
        duration = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"\nSelesai! Berhasil mengupdate pembobotan untuk {total_data} data dalam waktu {duration:.2f} detik tanpa terkena Timeout."
        ))