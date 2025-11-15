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
from core.utils import upload_to_supabase
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model


User = get_user_model()

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

    # 👇 Bunu ekliyoruz!
    last_seen_orders = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} ({self.gorev})"


# 🔔 Kullanıcı oluşturulunca profilini aç
@receiver(post_save, sender=User)
def create_profile_for_user(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile_for_user(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)


# 💰 Para birimi seçenekleri
CURRENCY_CHOICES = (
    ("TRY", "TRY"),
    ("USD", "USD"),
    ("EUR", "EUR"),
)


# 💵 Ürün Maliyeti Modeli
class ProductCost(models.Model):
    urun_kodu = models.CharField(max_length=100, unique=True)
    maliyet = models.DecimalField(max_digits=12, decimal_places=2)
    para_birimi = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="TRY")

    def __str__(self):
        return f"{self.urun_kodu} - {self.maliyet} {self.para_birimi}"


class Musteri(models.Model):
    ad = models.CharField(max_length=200, db_index=True)
    aktif = models.BooleanField(default=True)   # 👈 EKLENDİ!

    def __str__(self):
        return self.ad


class Nakisci(models.Model):
    ad = models.CharField(max_length=100)
    telefon = models.CharField(max_length=20, blank=True, null=True)
    notlar = models.TextField(blank=True, null=True)
    eklenme_tarihi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ad



class Fasoncu(models.Model):
    ad = models.CharField(max_length=100)
    telefon = models.CharField(max_length=20, blank=True, null=True)
    notlar = models.TextField(blank=True, null=True)
    eklenme_tarihi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ad




class Order(models.Model):
    SIPARIS_TIPLERI = [
        ('ÖZEL', 'Özel'),
        ('SERI', 'Seri'),
        ('STOK', 'Stoğa Üretim')  # 👈 Hazır üretim / depoya üretim tipi
    ]

    siparis_tipi = models.CharField(max_length=5, choices=SIPARIS_TIPLERI, null=True, blank=True, db_index=True)
    siparis_numarasi = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    musteri = models.ForeignKey('Musteri', on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    musteri_referans = models.CharField(max_length=150, blank=True, null=True, verbose_name="Müşteri Sipariş Referansı")

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
    cikti_alindi = models.BooleanField(default=False)

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
        choices=[
            ('bekliyor', 'Bekliyor'),
            ('hazirlaniyor', 'Hazırlanıyor'),
            ('gonderildi', 'Gönderildi')
        ],
        default='bekliyor'
    )

    dikim_fason = models.BooleanField(default=False)
    dikim_fasoncu = models.ForeignKey(Fasoncu, on_delete=models.SET_NULL, null=True, blank=True, related_name='dikim_fasonlari')
    dikim_fason_durumu = models.CharField(max_length=20, choices=[('verildi', 'Verildi'), ('alindi', 'Alındı')], blank=True, null=True)

    susleme_fason = models.BooleanField(default=False)
    susleme_fasoncu = models.ForeignKey(Fasoncu, on_delete=models.SET_NULL, null=True, blank=True, related_name='susleme_fasonlari')
    susleme_fason_durumu = models.CharField(max_length=20, choices=[('verildi', 'Verildi'), ('alindi', 'Alındı')], blank=True, null=True)

    nakisci = models.ForeignKey(Nakisci, on_delete=models.SET_NULL, null=True, blank=True, related_name='nakis_siparisleri')
    nakis_durumu = models.CharField(max_length=20, choices=[('yok', 'Yok'), ('verildi', 'Nakışa Verildi'), ('alindi', 'Nakıştan Alındı')], default='yok')

    satis_fiyati = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    para_birimi = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="TRY")
    maliyet_uygulanan = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    maliyet_para_birimi = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="TRY")
    maliyet_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ekstra_maliyet = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)



    @property
    def is_stok_siparis(self) -> bool:
        return self.siparis_tipi == 'STOK'

    @property
    def is_ozel_siparis(self) -> bool:
        return self.siparis_tipi == 'ÖZEL'

    @property
    def is_seri_siparis(self) -> bool:
        return self.siparis_tipi == 'SERI'


    @property
    def efektif_maliyet(self):
        return self.maliyet_override if self.maliyet_override is not None else self.maliyet_uygulanan

    @property
    def kar(self):
        if self.satis_fiyati is None or self.efektif_maliyet is None:
            return None
        if self.para_birimi != self.maliyet_para_birimi:
            return None
        return self.satis_fiyati - (self.efektif_maliyet or 0) - (self.ekstra_maliyet or 0)

    @property
    def toplam_maliyet(self):
        uygulanan = self.maliyet_override if self.maliyet_override is not None else self.maliyet_uygulanan or 0
        ekstra = self.ekstra_maliyet or 0
        return uygulanan + ekstra

    def save(self, *args, **kwargs):
        creating = self._state.adding

        if creating and not self.siparis_numarasi:
            prefix = self.siparis_tipi or "SP"
            last_order = Order.objects.filter(siparis_tipi=self.siparis_tipi).order_by("id").last()
            if last_order and last_order.siparis_numarasi:
                try:
                    num = int(''.join(filter(str.isdigit, last_order.siparis_numarasi))) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            self.siparis_numarasi = f"{prefix}{num:04d}"

        super().save(*args, **kwargs)

        if creating and not self.qr_code_url:
            base_url = getattr(settings, "BASE_URL", "http://127.0.0.1:8000")
            detail_url = f"{base_url}{reverse('order_detail', args=[self.pk])}"

            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(detail_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            from datetime import datetime
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            # 🔹 Benzersiz dosya ismi (örnek: qr_15_20251107_104512.png)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"qr_{self.pk}_{timestamp}.png"

            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
            bucket = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME)

            # 🚀 Dosyayı yükle
            response = bucket.upload(
                path=filename,
                file=buffer.getvalue(),
                file_options={"content-type": "image/png"},
            )

            error_attr = getattr(response, "error", None)
            if error_attr is None:
                public_url = bucket.get_public_url(filename)
                self.qr_code_url = public_url
                super().save(update_fields=["qr_code_url"])
            else:
                print("⚠️ Supabase upload error:", error_attr)

    @property
    def son_durum(self):
        """Siparişin genel durumunu (özetini) döner."""
        # Sevkiyat bittiyse en üst öncelikli durum
        if self.sevkiyat_durum == "gonderildi":
            return "Sevkiyat Tamamlandı ✅"
        # Hazır bittiyse
        elif self.hazir_durum == "bitti":
            return "Hazırlık Tamamlandı"
        # Süsleme bittiyse
        elif self.susleme_durum == "bitti":
            return "Süsleme Tamamlandı"
        # Dikim bittiyse
        elif self.dikim_durum == "bitti":
            return "Dikim Tamamlandı"
        # Kesim bittiyse
        elif self.kesim_durum == "bitti":
            return "Kesim Tamamlandı"
        # Hiçbiri bitmemişse
        else:
            return "Bekliyor ⏳"


class OrderImage(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='extra_images')
    image = models.ImageField(upload_to='temp_uploads/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    image_url = models.URLField(blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Eğer image_url boşsa Supabase'e yükle
        if self.image and not self.image_url:
            try:
                # Dosyayı güvenli şekilde aç
                with open(self.image.path, "rb") as file_obj:
                    public_url = upload_to_supabase(file_obj)

                # Eğer başarılıysa image_url alanına kaydet
                if public_url:
                    self.image_url = public_url
                    super().save(update_fields=['image_url'])

            except Exception as e:
                print(f"⚠️ Supabase upload hatası: {e}")



import requests
import os

def upload_to_supabase(file_obj):
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
    SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET_NAME', 'qr-codes')

    file_name = os.path.basename(file_obj.name)
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{file_name}"

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/octet-stream"
    }

    response = requests.post(upload_url, headers=headers, data=file_obj.read())
    if response.status_code in (200, 201):
        return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{file_name}"
    else:
        print("Supabase upload failed:", response.text)
        return None


# 📜 ÜRETİM GEÇMİŞİ
class OrderEvent(models.Model):
    GOREV_SECENEKLERI = UserProfile.GOREV_SECENEKLERI

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    user = models.CharField(max_length=100)
    gorev = models.CharField(max_length=20, choices=GOREV_SECENEKLERI, default="yok")
    stage = models.CharField(max_length=100)
    value = models.CharField(max_length=200)
    adet = models.PositiveIntegerField(default=1)
    parca = models.CharField(max_length=100, blank=True, null=True)
    aciklama = models.TextField(blank=True, null=True)
    ortak_calisanlar = models.CharField(max_length=255, blank=True, null=True)
    fasoncu = models.ForeignKey(Fasoncu, on_delete=models.SET_NULL, null=True, blank=True)
    nakisci = models.ForeignKey(Nakisci, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    # 🆕 Sipariş düzenleme logları için
    event_type = models.CharField(
        max_length=20,
        choices=[
            ("stage", "Aşama Güncellemesi"),
            ("order_update", "Sipariş Güncellemesi"),
        ],
        default="stage"
    )

    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.order} | {self.stage} → {self.value} ({self.user})"

    class Meta:
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["user"]),
            models.Index(fields=["stage"]),
            models.Index(fields=["event_type"]),
        ]



# 🏬 DEPO STOK MODELİ
class DepoStok(models.Model):
    DEPO_SECENEKLERI = [
        ('KORIDOR', 'Koridor'),
        ('SHOWROOM', 'Showroom'),
        ('SHOWROOM_MUTF', 'Showroom Mutfak'),
        ('DANTEL_YANI', 'Dantel Odası Yanı'),
        ('ELISI', 'Elişi Deposu'),
    ]

    urun_kodu = models.CharField(max_length=100, db_index=True)
    renk = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    beden = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    adet = models.PositiveIntegerField(default=0)
    depo = models.CharField(max_length=20, choices=DEPO_SECENEKLERI, default='KORIDOR')
    aciklama = models.TextField(blank=True, null=True)
    eklenme_tarihi = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='stok_kaydi')

    def __str__(self):
        return f"{self.urun_kodu} - {self.renk}/{self.beden} ({self.depo}) [{self.adet} adet]"

class UretimGecmisi(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="uretim_kayitlari"
    )
    urun = models.CharField(max_length=100)
    asama = models.CharField(max_length=100)
    aciklama = models.TextField(blank=True, null=True)
    tarih = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.urun} - {self.asama}"



class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notification_set")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)

    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)

    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → {self.title}"




class OrderSeen(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    seen_time = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'order')

    def __str__(self):
        return f"{self.user} → {self.order}"







