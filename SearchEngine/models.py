from django.db import models
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

class DokumenAkademik(models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    title = models.TextField()
    author = models.TextField(null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    date_release = models.DateField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=50)
    type = models.CharField(max_length=100, null=True, blank=True)
    division = models.CharField(max_length=255, null=True, blank=True)
    relation = models.TextField(null=True, blank=True)
    file_url = models.TextField(null=True, blank=True)
    source_url = models.TextField(null=True, blank=True)
    indexed_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'SearchEngine_dokumenakademik'
        indexes = [
            GinIndex(fields=['search_vector']),
        ]
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update pembobotan setelah menyimpan dokumen
        vector = (
            SearchVector(Coalesce('title', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='A', config='indonesian') +
            SearchVector(Coalesce('author', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='B', config='indonesian') +
            SearchVector(Coalesce('abstract', Value('', output_field=models.TextField()), output_field=models.TextField()), weight='C', config='indonesian')
        )
        DokumenAkademik.objects.filter(pk=self.pk).update(search_vector=vector)

# Model untuk menyimpan tren pencarian
class SearchTrend(models.Model):
    keyword = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.keyword
    
# Sinyal untuk mengupdate versi cache setiap kali ada perubahan data pada DokumenAkademik
@receiver([post_save, post_delete], sender=DokumenAkademik)
def increment_cache_version(sender, **kwargs):
    current_version = cache.get('search_cache_version', 1)
    cache.set('search_cache_version', current_version + 1, timeout=None)