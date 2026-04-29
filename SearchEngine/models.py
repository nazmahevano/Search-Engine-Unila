from django.db import models
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db.models import Value
from django.db.models.functions import Coalesce

class DokumenAkademik(models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    title = models.TextField()
    author = models.TextField(null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    date_release = models.DateField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=50)
    access = models.CharField(max_length=20, default='public')
    type = models.CharField(max_length=100, null=True, blank=True)
    division = models.CharField(max_length=255, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    relation = models.TextField(null=True, blank=True)
    file_url = models.TextField(null=True, blank=True)
    source_url = models.TextField(null=True, blank=True)
    indexed_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        managed = False # Tetap False karena tabel dibuat manual di Supabase
        db_table = 'SearchEngine_dokumenakademik'
    
    def save(self, *args, **kwargs):
        # 1. Simpan data ke database terlebih dahulu seperti biasa
        super().save(*args, **kwargs)
        
        # 2. Setelah tersimpan dan mendapatkan ID, langsung perbarui bobot pencariannya khusus untuk data ini
        vector = (
            SearchVector(Coalesce('title', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='A', config='indonesian') +
            SearchVector(Coalesce('author', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='B', config='indonesian') +
            SearchVector(Coalesce('abstract', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='C', config='indonesian')
        )
        # Update langsung ke ID dokumen yang baru saja disave
        DokumenAkademik.objects.filter(pk=self.pk).update(search_vector=vector)