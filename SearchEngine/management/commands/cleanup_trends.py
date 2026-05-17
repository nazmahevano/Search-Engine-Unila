from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from SearchEngine.models import SearchTrend

class Command(BaseCommand):
    help = 'Menghapus riwayat tren pencarian yang usianya lebih dari 30 hari'

    def handle(self, *args, **kwargs):
        # Tentukan batas waktu: Hari ini mundur 30 hari ke belakang
        batas_waktu = timezone.now() - timedelta(days=30)
        
        # Hapus semua data yang lebih tua dari batas waktu
        jumlah_dihapus, _ = SearchTrend.objects.filter(created_at__lt=batas_waktu).delete()
        
        self.stdout.write(self.style.SUCCESS(f'Berhasil menghapus {jumlah_dihapus} data tren pencarian kedaluwarsa.'))