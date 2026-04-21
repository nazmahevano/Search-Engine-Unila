from rest_framework import serializers
from .models import DokumenAkademik

class DokumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DokumenAkademik
        fields = '__all__' # Kasih semua kolom ke Rifdah