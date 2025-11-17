from django.core.management.base import BaseCommand
from core.models import Order, DepoStok, UretimGecmisi
from django.db.models import Max

class Command(BaseCommand):
    help = "Üretim geçmişindeki son depoya göre DepoStok kayıtlarını düzeltir."

    def handle(self, *args, **options):
        orders = Order.objects.all()
        toplam = orders.count()
        duzeltildi = 0

        for order in orders:
            # 1) Üretim geçmişinde depo kayıtlarını bul
            gecmis = UretimGecmisi.objects.filter(order=order, asama="Depoya Girdi").order_by("-tarih")

            if not gecmis.exists():
                # Siparişin depoya giriş kaydı yok → tüm stokları sil
                DepoStok.objects.filter(order=order).delete()
                continue

            # 2) Son depoya giriş
            son = gecmis.first()
            hedef_depo = son.aciklama.strip()  # aciklama = depo adı

            # 3) DepoStok kontrol
            depo_kayitlari = DepoStok.objects.filter(order=order)

            # ❌ başka depolarda varsa → sil
            depo_kayitlari.exclude(depo=hedef_depo).delete()

            # ✔ hedef depoda kayıt yoksa → oluştur
            if not depo_kayitlari.filter(depo=hedef_depo).exists():
                DepoStok.objects.create(
                    order=order,
                    urun_kodu=order.urun_kodu,
                    renk=order.renk,
                    beden=order.beden,
                    adet=order.adet or 1,
                    depo=hedef_depo,
                    aciklama="Otomatik depo düzeltme"
                )

            duzeltildi += 1

        self.stdout.write(self.style.SUCCESS(f"✔ Depo temizlik tamamlandı. {duzeltildi}/{toplam} sipariş düzeltildi."))
