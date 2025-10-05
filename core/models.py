from django.db import models
from django.utils import timezone
from django.urls import reverse
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile


class Musteri(models.Model):
    ad = models.CharField(max_length=200)

    def __str__(self):
        return self.ad


class Order(models.Model):
    SIPARIS_TIPLERI = [
        ('ÖZEL', 'Özel'),
        ('SERI', 'Seri'),
    ]

    siparis_tipi = models.CharField(
        max_length=5,
        choices=SIPARIS_TIPLERI,
        null=True,
        blank=True
    )
    siparis_numarasi = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )
    musteri = models.ForeignKey(
        Musteri,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    siparis_tarihi = models.DateField(
        default=timezone.now,
        null=True,
        blank=True
    )
    urun_kodu = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    adet = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # 🆕 Renk ve Beden alanları
    renk = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )
    beden = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    teslim_tarihi = models.DateField(
        null=True,
        blank=True
    )
    aciklama = models.TextField(
        blank=True,
        null=True
    )
    resim = models.ImageField(
        upload_to='siparis_resimleri/',
        blank=True,
        null=True
    )
    qr_code = models.ImageField(
        upload_to='qr_codes/',
        blank=True,
        null=True
    )

    # 🧱 Üretim aşamaları
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
        # 1️⃣ Sipariş numarası otomatik oluştur
        if not self.siparis_numarasi and self.siparis_tipi:
            prefix = "ÖZEL" if self.siparis_tipi == "ÖZEL" else "SERI"
            last_order = Order.objects.filter(
                siparis_tipi=self.siparis_tipi
            ).order_by("id").last()
            if last_order and last_order.siparis_numarasi:
                try:
                    num = int(last_order.siparis_numarasi.replace(prefix, "")) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            self.siparis_numarasi = f"{prefix}{num:04d}"

        super().save(*args, **kwargs)  # önce kaydet ki pk oluşsun

        # 2️⃣ QR kodu oluştur
        if not self.qr_code:
            detail_url = f"http://127.0.0.1:8000{reverse('order_detail', args=[self.pk])}"

            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(detail_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            filename = f"qr_{self.pk}.png"

            self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
            super().save(update_fields=["qr_code"])

    def __str__(self):
        return f"{self.siparis_numarasi or 'NO_NUM'} - {self.musteri or 'Müşteri Yok'}"
