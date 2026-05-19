from django.db import migrations, models
import django.contrib.postgres.indexes

def create_search_trend_if_missing(apps, schema_editor):
    # Ambil model SearchTrend secara internal
    SearchTrend = apps.get_model('SearchEngine', 'SearchTrend')
    # Cek secara resmi ke sistem, jika tabel belum ada di Postgres, buatkan!
    if SearchTrend._meta.db_table not in schema_editor.connection.introspection.table_names():
        schema_editor.create_model(SearchTrend)

def add_gin_index_if_missing(apps, schema_editor):
    DokumenAkademik = apps.get_model('SearchEngine', 'DokumenAkademik')
    # Pasang GIN Index dengan aman, jika sudah ada jangan bikin error
    try:
        index = django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='SearchEngin_search__5181e3_gin')
        schema_editor.add_index(DokumenAkademik, index)
    except Exception:
        pass

class Migration(migrations.Migration):

    dependencies = [
        # ⚠️ GANTI TULISAN DI BAWAH INI SESUAI NAMA FILE 0003 LO DI VSCODE LAPTOP
        ('SearchEngine', '0003_dokumenakademik_searchengin_search__5181e3_gin'),
    ]

    operations = [
        # Jalankan pembuatan tabel & index hanya jika mendeteksi pangkalan data server belum punya
        migrations.RunPython(create_search_trend_if_missing, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(add_gin_index_if_missing, reverse_code=migrations.RunPython.noop),
        
        # Perbaiki ingatan internal Django tentang kolom hantu tanpa eksekusi SQL drop ke database
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='dokumenakademik',
                    name='diambil_pada',
                ),
                migrations.RemoveField(
                    model_name='dokumenakademik',
                    name='url_asli',
                ),
            ]
        )
    ]