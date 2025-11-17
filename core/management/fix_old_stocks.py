from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Order, OrderEvent, DepoStok
import re

class Command(BaseCommand):
    help = "Tüm siparişleri tarar, üretim geçmişinin son kaydına göre depoları otomatik düzeltir."

    def normalize_depo_name(self, text):
        t = text.lower().strip()
        t = (
            t.replace("ı", "i")
             .replace("ş", "s")
             .replace("ğ", "g")
             .replace("ü", "u")
             .replace("ö", "o")
             .replace("ç", "c")
        )
        t = t.replace(" ", "_")
        return t

    def handle(self, *args, **kwargs):
        DEPO_MAP = {
            "koridor": "KORIDOR",
            "showroom": "SHOWROOM",
            "showroom_mutfak": "SHOWROOM_MUTF",
            "dantel_odasi_yani": "DANTEL_YANI",
            "elisi_deposu": "ELISI",
        }

        count_fixed = 0
        count_deleted = 0

        all_orders = Order.objects.all()

        self.stdout.write(self.style.WARNING(f"🔍 {all_orders.count()} sipariş taranıyor..."))

        for order in all_orders:
            last_event = (
                OrderEvent.objects.filter(order=order)
                .order_by("-timestamp")
                .first()
            )

            # 🔹 Önce mevcut stokları temizle
            DepoStok.objects.filter(order=order).delete()

            if not last_event:
                continue

            text = last_event.value or ""
            match = re.search(r"\((.*?)\)", text)

            if match:
                depo_raw = match.group(1)
                key = self.normalize_depo_name(depo_raw)
                depo_code = DEPO_MAP.get(key)

                if depo_code:
                    DepoStok.objects.create(
                        urun_kodu=order.urun_kodu,
                        renk=order.renk,
                        beden=order.beden,
                        adet=order.adet or 1,
                        depo=depo_code,
                        aciklama=f"Otomatik Düzeltme: {depo_code}",
                        order=order
                    )

                    count_fixed += 1
            else:
                # depo yoksa → stok oluşturma, boş bırak
                count_deleted += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Düzeltme bitti!"))
        self.stdout.write(self.style.SUCCESS(f"📦 Yeni oluşturulan depo kayıtları: {count_fixed}"))
        self.stdout.write(self.style.SUCCESS(f"🗑️ Silinen depo kayıtları: {count_deleted}"))
