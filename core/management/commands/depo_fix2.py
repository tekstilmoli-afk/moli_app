from django.core.management.base import BaseCommand
from core.models import Order, DepoStok, UretimGecmisi
from django.db import transaction

class Command(BaseCommand):
    help = "DepoStok kayıtlarını üretim geçmişindeki son depoya göre hızlı şekilde düzeltir."

    def handle(self, *args, **options):
        orders = Order.objects.all().only("id", "urun_kodu", "renk", "beden", "adet")
        toplam = orders.count()
        duzeltildi = 0

        self.stdout.write(self.style.WARNING("⏳ Depo düzeltme başlıyor..."))

        for order in orders:
            # 1) Üretim geçmişinde Depoya Girdi kayıtlarını bul
            son_kayit = (
                UretimGecmisi.objects
                .filter(order_id=order.id, asama="Depoya Girdi")
                .order_by("-tarih")
                .first()
            )

            # Depoya hiç girmemiş -> tüm depo kayıtlarını sil
            if not son_kayit:
                DepoStok.objects.filter(order_id=order.id).delete()
                continue

            hedef_depo = son_kayit.aciklama.strip()

            # 2) Mevcut depo kayıtlarını al
            mevcut = DepoStok.objects.filter(order_id=order.id)

            # 3) Yanlış depoları sil
            mevcut.exclude(depo=hedef_depo).delete()

            # 4) Doğru depoda yoksa oluştur
            if not mevcut.filter(depo=hedef_depo).exists():
                DepoStok.objects.create(
                    order_id=order.id,
                    urun_kodu=order.urun_kodu,
                    renk=order.renk,
                    beden=order.beden,
                    adet=order.adet or 1,
                    depo=hedef_depo,
                    aciklama="Otomatik depo düzeltme"
                )

            duzeltildi += 1

        self.stdout.write(self.style.SUCCESS(
            f"✔ Depo düzeltme tamamlandı. {duzeltildi}/{toplam} sipariş işlendi."
        ))
