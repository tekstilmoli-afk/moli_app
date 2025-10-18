from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
import qrcode
from io import BytesIO
from supabase import create_client, Client

# ✅ Supabase client başlat
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

User = get_user_model()

# 👤 Kullanıcı Profili (Görev)
class UserProfile(models.Model):
    GOREV_SECENEKLERI = [
        ("yok", "Yok"),
        ("kesim", "Kesim"),
        ("dikim", "Dikim"),
        ("susleme", "Süsleme"),
        ("hazir", "Hazır"),
        ("sevkiyat", "Sevkiyat"),
        ("nakis", "Nakış"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    gorev = models.CharField(max_length=20, choices=GOREV_SECENEKLERI, default="yok")

    def __str__(self):
        return f"{self.user.username} ({self.gorev})"

# 🔔 Kullanıcı oluşturulunca profilini aç
@receiver(post_save, sender=User)
def create_profile_for_user(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile_for_user(sender, instance, **kwargs):
    # profil yoksa sessizce oluştur
    UserProfile.objects.get_or_create(user=instance)


class Musteri(models.Model):
    ad = models.CharField(max_length=200, db_index=True)
    def __str__(self):
        return self.ad


class Nakisci(models.Model):
    ad = models.CharField(max_length=100)
    def __str__(self):
        return self.ad


class Fasoncu(models.Model):
    ad = models.CharField(max_length=100)
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

    DURUM_SECENEKLERI = [
        ('bekliyor', 'Bekliyor'),
        ('basladi', 'Başladı'),
        ('bitti', 'Bitti'),
    ]

    kesim_durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='bekliyor')
    dikim_durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='bekliyor')
    susleme_durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='bekliyor')
    hazir_durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='bekliyor')
    sevkiyat_durum = models.CharField(
        max_length=20,
        choices=[('bekliyor', 'Bekliyor'), ('hazirlaniyor', 'Hazırlanıyor'), ('gonderildi', 'Gönderildi')],
        default='bekliyor'
    )

    dikim_fason = models.BooleanField(default=False)
    dikim_fasoncu = models.ForeignKey(
        Fasoncu, on_delete=models.SET_NULL, null=True, blank=True, related_name='dikim_fasonlari'
    )
    dikim_fason_durumu = models.CharField(
        max_length=20,
        choices=[('verildi', 'Verildi'), ('alindi', 'Alındı')],
        blank=True,
        null=True
    )

    susleme_fason = models.BooleanField(default=False)
    susleme_fasoncu = models.ForeignKey(
        Fasoncu, on_delete=models.SET_NULL, null=True, blank=True, related_name='susleme_fasonlari'
    )
    susleme_fason_durumu = models.CharField(
        max_length=20,
        choices=[('verildi', 'Verildi'), ('alindi', 'Alındı')],
        blank=True,
        null=True
    )

    nakisci = models.ForeignKey(
        Nakisci, on_delete=models.SET_NULL, null=True, blank=True, related_name='nakis_siparisleri'
    )
    nakis_durumu = models.CharField(
        max_length=20,
        choices=[('yok', 'Yok'), ('verildi', 'Nakışa Verildi'), ('alindi', 'Nakıştan Alındı')],
        default='yok'
    )

    def save(self, *args, **kwargs):
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

        super().save(*args, **kwargs)

        base_url = getattr(settings, "BASE_URL", "http://127.0.0.1:8000")
        detail_url = f"{base_url}{reverse('order_detail', args=[self.pk])}"

        if not self.qr_code_url:
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(detail_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            filename = f"qr_{self.pk}.png"

            response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                path=filename,
                file=buffer.getvalue(),
                file_options={"content-type": "image/png"}
            )

            error_attr = getattr(response, "error", None)
            if error_attr is None:
                public_url = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(filename)
                self.qr_code_url = public_url
                super().save(update_fields=["qr_code_url"])
            else:
                print("⚠️ Supabase upload error:", error_attr)

    def __str__(self):
        return f"{self.siparis_numarasi or 'NO_NUM'} - {self.musteri or 'Müşteri Yok'}"


# 📜 ÜRETİM GEÇMİŞİ
class OrderEvent(models.Model):
    GOREV_SECENEKLERI = UserProfile.GOREV_SECENEKLERI

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    user = models.CharField(max_length=100)
    gorev = models.CharField(max_length=20, choices=GOREV_SECENEKLERI, default="yok")
    stage = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.order} | {self.stage} → {self.value} ({self.user}, {self.gorev})"
