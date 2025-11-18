from django.core.management.base import BaseCommand
from core.models import Order, OrderEvent, DepoStok
import re

class Command(BaseCommand):
    help = "Var olan stokları güvenli şekilde düzeltir. Mevcut stokları SİLMEZ, sadece doğru depoya taşır."

    DEPO_MAP = {
        "koridor": "KORIDOR",
        "showroom": "SHOWROOM",
        "showroom_mutfak": "SHOWROOM_MUTF",
        "dantel_odasi_yani": "DANTEL_YANI",
        "elisi_deposu": "ELISI",
    }

    def normalize(self, text):
        t = text.lower().strip()
        t = (
            t.replace("ı", "i")
             .replace("ş", "s")
             .replace("ğ", "g")
             .replace("ü", "u")
             .replace("ö", "o")
             .replace("ç", "c")
        )
        return t.replace(" ", "_")

    def handle(self, *args, **kwargs):
        orders = Order.objects.all()
        moved = 0
        skipped = 0

        self.stdout.write(self.style.WARNING(f"🔎 {orders.count()} sipariş taranıyor..."))

        for order in orders:

            stok = DepoStok.objects.filter(order=order).first()

            # 📌 Bu siparişe ait stok yok → elle depoya gir yapılmamış → dokunma
            if not stok:
                skipped += 1
                continue

            last_event = OrderEvent.objects.filter(order=order).order_by("-timestamp").first()
            if not last_event:
                skipped += 1
                continue

            match = re.search(r"\((.*?)\)", last_event.value or "")

            # 📌 üretim geçmişinde depo yok → dokunma
            if not match:
                skipped += 1
                continue

            depo_raw = match.group(1)
            depo_key = self.normalize(depo_raw)
            depo_code = self.DEPO_MAP.get(depo_key)

            # 📌 üretim geçmişindeki depo geçerli değil → dokunma
            if not depo_code:
                skipped += 1
                continue

            # 📌 doğru depodaymış → taşımaya gerek yok
            if stok.depo == depo_code:
                skipped += 1
                continue

            # 📦 yanlış depoda → doğru depoya taşı
            stok.depo = depo_code
            stok.aciklama = f"Otomatik düzeltme: {depo_code} deposuna taşındı"
            stok.save()

            moved += 1

        self.stdout.write(self.style.SUCCESS("✅ İşlem tamamlandı!"))
        self.stdout.write(self.style.SUCCESS(f"📦 Doğru depoya taşınan stok: {moved}"))
        self.stdout.write(self.style.WARNING(f"⏸ Dokunulmayan (skipped): {skipped}"))
