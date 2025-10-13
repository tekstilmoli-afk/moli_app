from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
import qrcode
from io import BytesIO
from supabase import create_client, Client  # 👈 Supabase kütüphanesi

# ✅ Supabase client başlat
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


class Musteri(models.Model):
    ad = models.CharField(max_length=200, db_index=True)

    def __str__(self):
        return self.ad


class Order(models.Model):
    SIPARIS_TIPLERI = [
        ('ÖZEL', 'Özel'),
        ('SERI', 'Seri'),
    ]

    siparis_tipi = models.CharField(max_length=5, choices=SIPARIS_TIPLERI, null=True, blank=True, db_index=True)
    siparis_numarasi = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    musteri = models.ForeignKey('Musteri', on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    siparis_tarihi = models.DateField(default=timezone.now, null=True, blank=True, db_index=True)
    urun_kodu = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    adet = models.PositiveIntegerField(null=True, blank=True)
    renk = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    beden = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    teslim_tarihi = models.DateField(null=True, blank=True, db_index=True)
    aciklama = models.TextField(blank=True, null=True)
    resim = models.ImageField(upload_to='siparis_resimleri/', blank=True, null=True)

    # ⬇️ QR kod dosyası yerine sadece URL tutuluyor
    qr_code_url = models.URLField(blank=True, null=True)

    kesim_yapan = models.CharField(max_length=100, blank=True, null=True)
    kesim_tarihi = models.DateTimeField(blank=True, null=True)
    dikim_yapan = models.CharField(max_length=100, blank=True, null=True)
    dikim_tarihi = models.DateTimeField(blank=True, null=True)
    susleme_yapan = models.CharField(max_length=100, blank=True, null=True)
    susleme_tarihi = models.DateTimeField(blank=True, null=True)
    hazir_yapan = models.CharField(max_length=100, blank=True, null=True)
    hazir_tarihi = models.DateTimeField(blank=True, null=True)
    sevkiyat_yapan = models.CharField(max_length=100, blank=True, null=True)
    sevkiyat_tarihi = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # 🆔 Sipariş numarası otomatik üretimi
        if not self.siparis_numarasi and self.siparis_tipi:
            prefix = "ÖZEL" if self.siparis_tipi == "ÖZEL" else "SERI"
            last_order = Order.objects.filter(siparis_tipi=self.siparis_tipi).order_by("id").last()
            if last_order and last_order.siparis_numarasi:
                try:
                    num = int(last_order.siparis_numarasi.replace(prefix, "")) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            self.siparis_numarasi = f"{prefix}{num:04d}"

        # Önce kaydedip pk alalım
        super().save(*args, **kwargs)

        # 🌐 Ortama göre QR kod URL'si
        base_url = getattr(settings, "BASE_URL", "http://127.0.0.1:8000")
        detail_url = f"{base_url}{reverse('order_detail', args=[self.pk])}"

        # 🧠 QR kod daha önce oluşturulmadıysa Supabase'e yükle
        if not self.qr_code_url:
            # QR üret
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(detail_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Bytes'a çevir
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            filename = f"qr_{self.pk}.png"

            # 📤 Supabase'e yükle
            response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                path=filename,
                file=buffer.getvalue(),
                file_options={"content-type": "image/png"}
            )

            # ✅ Yeni SDK: response bir UploadResponse objesi → .error özelliği var
            if not response.error:
                public_url = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(filename)
                self.qr_code_url = public_url
                super().save(update_fields=["qr_code_url"])
            else:
                print("⚠️ Supabase upload error:", response.error)

    def __str__(self):
        return f"{self.siparis_numarasi or 'NO_NUM'} - {self.musteri or 'Müşteri Yok'}"
