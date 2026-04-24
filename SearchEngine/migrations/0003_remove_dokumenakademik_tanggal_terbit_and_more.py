import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('SearchEngine', '0002_alter_dokumenakademik_tanggal_terbit'),
    ]

    operations = [
        # 1. Bikin Kolom (Cepat)
        migrations.AddField(
            model_name='dokumenakademik',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(blank=True, null=True),
        ),

        # 2. Bikin Index (Cepat)
        migrations.AddIndex(
            model_name='dokumenakademik',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='SearchEngin_search__620468_gin'),
        ),

        # 3. Pasang Trigger (Cepat)
        # Ini biar data baru otomatis masuk ke search_vector
        migrations.RunSQL(
            sql="""
                CREATE TRIGGER search_vector_update BEFORE INSERT OR UPDATE
                ON "SearchEngine_dokumenakademik" FOR EACH ROW EXECUTE FUNCTION
                tsvector_update_trigger(search_vector, 'pg_catalog.indonesian', title, abstract);
            """,
            reverse_sql="DROP TRIGGER IF EXISTS search_vector_update ON \"SearchEngine_dokumenakademik\";"
        ),
    ]