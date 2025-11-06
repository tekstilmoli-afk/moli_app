from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "PostgreSQL VACUUM ANALYZE işlemini haftalık olarak yapar."

    def handle(self, *args, **kwargs):
        self.stdout.write("🧹 PostgreSQL bakım işlemi başlatılıyor...")
        with connection.cursor() as cursor:
            cursor.execute("VACUUM (VERBOSE, ANALYZE);")
        self.stdout.write(self.style.SUCCESS("✅ Veritabanı başarıyla optimize edildi."))
