import os
import time
import json
import requests
from datetime import datetime, timedelta

from django.db import connections
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, Max, Count, Sum, F, ExpressionWrapper, FloatField, Subquery, OuterRef
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from core.models import Fasoncu
from .models import Order, Nakisci
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from .models import Order, DepoStok, OrderEvent
from django.db.models import Sum, Count, Max
from django.db.models import Q, Sum
from django.views.decorators.cache import never_cache
from .models import DepoStok, Order, UretimGecmisi
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import DepoStok, Order
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Musteri
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Musteri
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Musteri
from django.views.decorators.cache import never_cache
from .models import OrderSeen
import time
from django.contrib.auth import get_user_model
from .models import Notification
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce


from openpyxl import Workbook

# 🗑️ Sipariş Silme (Cache-aware + AJAX uyumlu)
from django.core.cache import cache

# 📦 Proje modelleri ve formlar
from .models import (
    Order,
    Musteri,
    Nakisci,
    Fasoncu,
    OrderEvent,
    UserProfile,
    ProductCost,
    OrderImage
)
from .forms import OrderForm, MusteriForm

# 🧠 Google Gemini AI REST (artık sadece requests ile çağrılıyor)
# NOT: google.generativeai modülü kaldırıldı (v1 API ile çakıştığı için)





# 🧠 Ortak filtreleme fonksiyonu
def apply_filters(request, qs):
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(siparis_numarasi__icontains=q)
            | Q(siparis_tipi__icontains=q)
            | Q(musteri__ad__icontains=q)
            | Q(urun_kodu__icontains=q)
            | Q(renk__icontains=q)
            | Q(beden__icontains=q)
            | Q(adet__icontains=q)
            | Q(siparis_tarihi__icontains=q)
            | Q(teslim_tarihi__icontains=q)
            | Q(aciklama__icontains=q)
        )

    filter_fields = {
        "siparis_tipi__in": request.GET.getlist("siparis_tipi"),
        "musteri__ad__in": request.GET.getlist("musteri"),
        "urun_kodu__in": request.GET.getlist("urun_kodu"),
        "renk__in": request.GET.getlist("renk"),
        "beden__in": request.GET.getlist("beden"),
        "adet__in": request.GET.getlist("adet"),
        "siparis_tarihi__in": request.GET.getlist("siparis_tarihi"),
        "teslim_tarihi__in": request.GET.getlist("teslim_tarihi"),
        "aciklama__in": request.GET.getlist("aciklama"),
    }
    for field, value in filter_fields.items():
        if value:
            qs = qs.filter(**{field: value})

    sort_col = request.GET.get("sort")
    sort_dir = request.GET.get("dir", "asc")
    if sort_col:
        qs = qs.order_by(f"-{sort_col}" if sort_dir == "desc" else sort_col)

    return qs

# 🖼️ Tek görseli tam ekranda görüntüleme
@login_required
def view_image(request, image_id):
    image = get_object_or_404(OrderImage, id=image_id)
    return render(request, "core/view_image.html", {"image": image})


# 📋 Sipariş Listeleme (Son Durum Gecikmesi Giderildi)
from django.db.models import OuterRef, Subquery, Q, Value, CharField
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.shortcuts import render
from core.models import Order, OrderEvent


from django.db import close_old_connections  # ⬅️ En üste import ekle

@never_cache
@login_required
def order_list(request):
    close_old_connections()
    connections["default"].close()

    # -----------------------------------------
    # 📌 1) TÜM SİPARİŞLERİ AL ve yeni/okunmamış hesapla
    # -----------------------------------------
    all_orders = Order.objects.only("id", "last_updated")

    # 📊 Tüm siparişlerin toplam adedi (filtre öncesi)
    total_count = Order.objects.count()


    seen_map = {
        s.order_id: s.seen_time
        for s in OrderSeen.objects.filter(user=request.user)
    }

    new_flags = {}
    for o in all_orders:
        last_seen = seen_map.get(o.id)
        if not last_seen:
            new_flags[o.id] = True
        else:
            new_flags[o.id] = o.last_updated > last_seen

    request.user.userprofile.last_seen_orders = timezone.now()
    request.user.userprofile.save(update_fields=["last_seen_orders"])

    # -----------------------------------------
    # 📌 2) TÜRKÇE DURUM SÖZLÜĞÜ
    # -----------------------------------------
    STAGE_TRANSLATIONS = {
        ("dikim_durum", "sıraya_alındı"): "Dikime Alındı",
        ("susleme_durum", "sıraya_alındı"): "Süsleme Sırasına Alındı",
        ("dikim_durum", "basladi"): "Dikime Başlandı",
        ("dikim_durum", "kismi_bitti"): "Kısmi Dikim Yapıldı",
        ("dikim_durum", "bitti"): "Dikim Bitti",
        ("kesim_durum", "basladi"): "Kesime Başlandı",
        ("kesim_durum", "kismi_bitti"): "Kısmi Kesim Yapıldı",
        ("kesim_durum", "bitti"): "Kesim Bitti",
        ("susleme_durum", "basladi"): "Süsleme Başladı",
        ("susleme_durum", "kismi_bitti"): "Kısmi Süsleme Yapıldı",
        ("susleme_durum", "bitti"): "Süsleme Bitti",
        ("dikim_fason_durumu", "verildi"): "Dikim İçin Fasona Verildi",
        ("dikim_fason_durumu", "alindi"): "Dikim Fasoncusundan Alındı",
        ("susleme_fason_durumu", "verildi"): "Süsleme İçin Fasona Verildi",
        ("susleme_fason_durumu", "alindi"): "Süsleme Fasoncusundan Alındı",
        ("sevkiyat_durum", "gonderildi"): "Sevkiyat Gönderildi",
    }

    # -----------------------------------------
    # 📌 3) EN SON EVENT
    # -----------------------------------------
    latest_event = (
        OrderEvent.objects
        .filter(order=OuterRef("pk"))
        .order_by("-id")[:1]
    )

    # -----------------------------------------
    # 📌 4) ANA QUERY
    # -----------------------------------------
    qs = (
        Order.objects.select_related("musteri")
        .only(
            "id", "siparis_numarasi", "siparis_tipi", "urun_kodu", "renk",
            "beden", "adet", "siparis_tarihi", "teslim_tarihi",
            "aciklama", "musteri__ad", "qr_code_url"
        )
        .annotate(
            latest_stage=Subquery(latest_event.values("stage")),
            latest_value=Subquery(latest_event.values("value")),
        )
        .order_by("-id")
    )

    # -----------------------------------------
    # 📌 5) FİLTRELER (DOĞRU HALİ)
    # -----------------------------------------
    siparis_nolar = request.GET.getlist("siparis_no")
    musteriler = request.GET.getlist("musteri")
    urun_kodlari = request.GET.getlist("urun_kodu")
    renkler = request.GET.getlist("renk")
    bedenler = request.GET.getlist("beden")
    status_filter = request.GET.getlist("status")
    siparis_tipleri = request.GET.getlist("siparis_tipi")

    if siparis_nolar:
        qs = qs.filter(siparis_numarasi__in=siparis_nolar)
    if musteriler:
        qs = qs.filter(musteri__ad__in=musteriler)
    if urun_kodlari:
        qs = qs.filter(urun_kodu__in=urun_kodlari)
    if renkler:
        qs = qs.filter(renk__in=renkler)
    if bedenler:
        qs = qs.filter(beden__in=bedenler)
    if siparis_tipleri:
        qs = qs.filter(siparis_tipi__in=siparis_tipleri)


    if status_filter:
        stage_value_pairs = [
            key for key, val in STAGE_TRANSLATIONS.items()
            if val in status_filter
        ]
        q = Q()
        for stage, value in stage_value_pairs:
            q |= Q(latest_stage=stage, latest_value=value)
        qs = qs.filter(q)

    teslim_baslangic = request.GET.get("teslim_tarihi_baslangic")
    teslim_bitis = request.GET.get("teslim_tarihi_bitis")

    if teslim_baslangic and teslim_bitis:
        qs = qs.filter(teslim_tarihi__range=[teslim_baslangic, teslim_bitis])
    elif teslim_baslangic:
        qs = qs.filter(teslim_tarihi__gte=teslim_baslangic)
    elif teslim_bitis:
        qs = qs.filter(teslim_tarihi__lte=teslim_bitis)

        # 📊 Filtrelenmiş sipariş adedi
    filtered_count = qs.count()


    # -----------------------------------------
    # 📌 6) SAYFALAMA
    # -----------------------------------------
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    # -----------------------------------------
    # 📌 7) is_new FLAGİNİ EKLE
    # -----------------------------------------
    for order in page_obj:
        order.is_new = new_flags.get(order.id, False)
        if order.latest_stage and order.latest_value:
            order.formatted_status = STAGE_TRANSLATIONS.get(
                (order.latest_stage, order.latest_value),
                f"{order.latest_stage.replace('_', ' ').title()} → {order.latest_value.title()}",
            )
        else:
            order.formatted_status = "-"

    # -----------------------------------------
    # 📌 8) CONTEXT
    # -----------------------------------------

    is_manager = request.user.groups.filter(name__in=["patron", "mudur"]).exists()

    context = {
        "orders": page_obj,
        "siparis_options": Order.objects.values_list("siparis_numarasi", flat=True).distinct().order_by("siparis_numarasi"),
        "musteri_options": Order.objects.values_list("musteri__ad", flat=True).distinct().order_by("musteri__ad"),
        "urun_options": Order.objects.values_list("urun_kodu", flat=True).distinct().order_by("urun_kodu"),
        "renk_options": Order.objects.values_list("renk", flat=True).distinct().order_by("renk"),
        "beden_options": Order.objects.values_list("beden", flat=True).distinct().order_by("beden"),
        "status_options": sorted(set(STAGE_TRANSLATIONS.values())),
        "siparis_tipi_options": Order.objects.values_list("siparis_tipi", flat=True).distinct().order_by("siparis_tipi"),
        "total_count": total_count,
        "filtered_count": filtered_count,
        "is_manager": is_manager,
    }

    response = render(request, "core/order_list.html", context)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response









@login_required
@never_cache
def order_create(request):
    if request.method == "POST":
        form = OrderForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            order = form.save(commit=False)

            urun_kodu = form.cleaned_data.get("urun_kodu")
            if urun_kodu:
                try:
                    from .models import ProductCost
                    maliyet_obj = ProductCost.objects.get(urun_kodu=urun_kodu)
                    order.maliyet_uygulanan = maliyet_obj.maliyet
                    order.maliyet_para_birimi = maliyet_obj.para_birimi
                except ProductCost.DoesNotExist:
                    order.maliyet_uygulanan = None

            order.save()
            cache.clear()
            return redirect(f"{reverse('order_list')}?t={int(time.time())}")
    else:
        form = OrderForm(user=request.user)

    is_manager = request.user.groups.filter(name__in=["patron", "mudur"]).exists()

    # ✅ Modalda kullanmak için aktif müşteriler → GEREKLİ!
    aktif_musteriler = Musteri.objects.filter(aktif=True).order_by("ad")

    return render(request, "core/order_form.html", {
        "form": form,
        "is_manager": is_manager,
        "aktif_musteriler": aktif_musteriler,   # ← EKLENDİ
    })






# 👤 Yeni Müşteri
@login_required
def musteri_create(request):
    if request.method == "POST":
        form = MusteriForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("order_create")
    else:
        form = MusteriForm()
    return render(request, "core/musteri_form.html", {"form": form})


# 🧠 Müşteri arama (autocomplete)
@login_required
def musteri_search(request):
    term = request.GET.get("term", "")
    qs = Musteri.objects.filter(ad__icontains=term).values_list("ad", flat=True)[:20]
    return JsonResponse(list(qs), safe=False)


@login_required
@never_cache
def order_detail(request, pk):
    # 📌 Önce siparişi çek
    order = get_object_or_404(Order.objects.select_related("musteri"), pk=pk)

    # 👁️ Kullanıcı bu siparişi gördü olarak işaretle
    OrderSeen.objects.update_or_create(
        user=request.user,
        order=order,
        defaults={"seen_time": timezone.now()}
    )

    # 📌 Diğer veriler
    nakisciler = Nakisci.objects.all()
    fasoncular = Fasoncu.objects.all()

    # 🔹 Üretim event'leri
    events = OrderEvent.objects.filter(order=order).order_by("-timestamp")
    update_events = events.filter(event_type="order_update")

    # 🔒 Personel fiyat değişikliklerini görmesin
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        gizli_alanlar = [
            "satis_fiyati",
            "ekstra_maliyet",
            "maliyet_override",
            "maliyet_uygulanan",
        ]
        events = events.exclude(stage__in=gizli_alanlar)
        update_events = update_events.exclude(stage__in=gizli_alanlar)

    # 🔥 Depo / Hazırdan Verilen Ürün Hareketleri
    uretim_kayitlari = UretimGecmisi.objects.filter(order=order).order_by("-tarih")

    is_manager = request.user.groups.filter(name__in=["patron", "mudur"]).exists()

    return render(
        request,
        "core/order_detail.html",
        {
            "order": order,
            "nakisciler": nakisciler,
            "fasoncular": fasoncular,
            "events": events,
            "update_events": update_events,
            "is_manager": is_manager,
            "uretim_kayitlari": uretim_kayitlari,
        },
    )





@login_required
def depo_ozet(request):
    depo_ozetleri = (
        DepoStok.objects
        .values('depo')
        .annotate(
            toplam_adet=Sum('adet'),
            kayit_sayisi=Count('id'),
            son_guncelleme=Max('eklenme_tarihi')  # ✅ düzeltildi
        )
        .order_by('depo')
    )

    return render(request, 'depolar/ozet.html', {'depolar': depo_ozetleri})

# 🔐 Özel Login (hızlı ve güvenli)
@csrf_exempt
def custom_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            user_groups = list(user.groups.values_list("name", flat=True))
            next_url = request.GET.get("next", "/")

            if next_url and next_url not in ["/", "/management/"]:
                return redirect(next_url)

            if any(role in user_groups for role in ["patron", "mudur"]):
                return redirect("/management/")
            else:
                return redirect("/")
        else:
            return render(request, "registration/custom_login.html", {"error": True})

    return render(request, "registration/custom_login.html")



@login_required
def update_stage(request, pk):
    order = get_object_or_404(Order, pk=pk)
    stage = request.GET.get("stage") or request.POST.get("stage")
    value = request.GET.get("value") or request.POST.get("value")
    is_production_count = request.GET.get("is_production_count") or request.POST.get("is_production_count")

    # ❗ Ön kontrol
    if not stage or not value:
        return HttpResponseForbidden("Eksik veri")

    # ---------------------------------------------------------
    # 1️⃣ SİPARİŞ ÜZERİNDE AŞAMAYI GÜNCELLE
    # ---------------------------------------------------------
    try:
        setattr(order, stage, value)
        order.save(update_fields=[stage])
    except Exception as e:
        print("Aşama güncelleme hatası:", e)

    # ---------------------------------------------------------
    # 2️⃣ ÜRETİM GEÇMİŞİNE KAYIT OLUŞTUR
    # ---------------------------------------------------------
    try:
        display_value = dict(Order.DURUM_SECENEKLERI).get(value, value)

        OrderEvent.objects.create(
            order=order,
            user=request.user.username,
            gorev=stage.replace("_durum", ""),
            stage=stage,
            value=display_value,
            adet=order.adet or 1,
            event_type="stage"
        )
    except Exception as e:
        print("Üretim geçmişi hatası:", e)

    # ---------------------------------------------------------
    # 3️⃣ DEPO OTOMATİĞİ
    # ---------------------------------------------------------
    import re

    def normalize_depo_name(text):
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

    DEPO_MAP = {
        "koridor": "KORIDOR",
        "showroom": "SHOWROOM",
        "showroom_mutfak": "SHOWROOM_MUTF",
        "dantel_odasi_yani": "DANTEL_YANI",
        "elisi_deposu": "ELISI",
    }

    try:
        match = re.search(r"\((.*?)\)", value or "")

        if not match:
            DepoStok.objects.filter(order=order).delete()
        else:
            depo_raw = match.group(1)
            key = normalize_depo_name(depo_raw)
            depo_code = DEPO_MAP.get(key)

            if not depo_code:
                DepoStok.objects.filter(order=order).delete()
            else:
                DepoStok.objects.filter(order=order).delete()
                DepoStok.objects.create(
                    urun_kodu=order.urun_kodu,
                    renk=order.renk,
                    beden=order.beden,
                    adet=order.adet or 1,
                    depo=depo_code,
                    aciklama=f"Otomatik Depo Kaydı: {depo_code}",
                    order=order
                )
    except Exception as e:
        print("⚠️ Depo otomatik hata:", e)

    # ---------------------------------------------------------
    # 4️⃣ HTMX isteği ise paneli geri gönder
    # ---------------------------------------------------------
    if request.headers.get("HX-Request"):
        return render(request, "core/_uretim_paneli.html", {
            "order": order,
            "events": OrderEvent.objects.filter(order=order).order_by("-timestamp")
    })


    # ---------------------------------------------------------
    # 5️⃣ Normal istek ise JSON
    # ---------------------------------------------------------
    return JsonResponse({"status": "ok"})







# ✅ Ürün resmi yüklemek / değiştirmek için fonksiyon
@login_required
def order_upload_image(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == "POST" and request.FILES.get("resim"):
        order.resim = request.FILES["resim"]
        order.save()

    return redirect("order_detail", pk=order.pk)

@login_required
@never_cache
def order_edit(request, pk):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    order = get_object_or_404(Order, pk=pk)

    # 🛡️ Yetki kontrolü
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu işlemi yapma yetkiniz yok.")

    # 📌 Güncellemeden önce eski hali sakla
    old_data = {
        "musteri": str(order.musteri) if order.musteri else None,
        "siparis_tipi": order.siparis_tipi,
        "urun_kodu": order.urun_kodu,
        "renk": order.renk,
        "beden": order.beden,
        "adet": order.adet,
        "aciklama": order.aciklama,
        "musteri_referans": order.musteri_referans,
        "teslim_tarihi": order.teslim_tarihi,
        "satis_fiyati": order.satis_fiyati,
        "ekstra_maliyet": order.ekstra_maliyet,
        "maliyet_override": order.maliyet_override,
    }

    if request.method == "POST":
        form = OrderForm(request.POST, request.FILES, instance=order, user=request.user)

        if form.is_valid():
            updated_order = form.save()
            updated_order.refresh_from_db()   # 🔥 Değişiklikleri anında getir

            # ------------------------------------------------------------
            # 🔥 KAR / MALİYET / FİYAT HESAPLAMASINI ANINDA TETİKLE
            # ------------------------------------------------------------
            _ = updated_order.efektif_maliyet
            _ = updated_order.toplam_maliyet
            _ = updated_order.kar_backend
            _ = updated_order.kar     # (frontend property)

            # ------------------------------------------------------------
            # 🔥 DEĞİŞİKLİK TESPİTİ
            # ------------------------------------------------------------
            new_data = {
                "musteri": str(updated_order.musteri) if updated_order.musteri else None,
                "siparis_tipi": updated_order.siparis_tipi,
                "urun_kodu": updated_order.urun_kodu,
                "renk": updated_order.renk,
                "beden": updated_order.beden,
                "adet": updated_order.adet,
                "aciklama": updated_order.aciklama,
                "musteri_referans": updated_order.musteri_referans,
                "teslim_tarihi": updated_order.teslim_tarihi,
                "satis_fiyati": updated_order.satis_fiyati,
                "ekstra_maliyet": updated_order.ekstra_maliyet,
                "maliyet_override": updated_order.maliyet_override,
            }

            changed_fields = []

            for field, old_value in old_data.items():
                new_value = new_data[field]
                if str(old_value) != str(new_value):
                    changed_fields.append(field)

                    # 🔥 Güncelleme logu
                    OrderEvent.objects.create(
                        order=updated_order,
                        user=request.user.username,
                        gorev="yok",
                        stage=field,
                        value=f"{field} değişti",
                        event_type="order_update",
                        old_value=str(old_value),
                        new_value=str(new_value),
                    )

            # ------------------------------------------------------------
            # 🔔 BİLDİRİM GÖNDER (eğer değişiklik varsa)
            # ------------------------------------------------------------
            if changed_fields:
                from .models import Notification

                alan_etiketleri = {
                    "musteri": "Müşteri",
                    "siparis_tipi": "Sipariş Tipi",
                    "urun_kodu": "Ürün Kodu",
                    "renk": "Renk",
                    "beden": "Beden",
                    "adet": "Adet",
                    "aciklama": "Açıklama",
                    "musteri_referans": "Müşteri Ref",
                    "teslim_tarihi": "Teslim Tarihi",
                    "satis_fiyati": "Satış Fiyatı",
                    "ekstra_maliyet": "Ekstra Maliyet",
                    "maliyet_override": "Manuel Maliyet",
                }

                okunur_alanlar = [alan_etiketleri.get(f, f) for f in changed_fields]
                degisen_text = ", ".join(okunur_alanlar)

                title = f"{updated_order.siparis_numarasi} güncellendi"
                message = f"Değişen alanlar: {degisen_text}. Güncelleyen: {request.user.username}"

                notif_list = [
                    Notification(
                        user=u,
                        order=updated_order,
                        title=title,
                        message=message,
                    )
                    for u in User.objects.all()
                ]

                Notification.objects.bulk_create(notif_list)

            # ------------------------------------------------------------
            # 🚀 CACHE TEMİZLE – KESİN GEREKİYOR!!!
            # ------------------------------------------------------------
            from django.core.cache import cache
            cache.clear()

            # ------------------------------------------------------------
            # 🚀 Sayfayı yenileyerek sonucunu göster
            # ------------------------------------------------------------
            return redirect(f"{reverse('order_detail', args=[pk])}?t={int(time.time())}")

    else:
        form = OrderForm(instance=order, user=request.user)

    is_manager = request.user.groups.filter(name__in=["patron", "mudur"]).exists()

    return render(request, "core/order_form.html", {
        "form": form,
        "order": order,
        "edit_mode": True,
        "is_manager": is_manager,
    })








@login_required
def order_add_image(request, pk):
    order = get_object_or_404(Order, pk=pk)

    # 🛡️ Yalnızca patron veya müdür yükleme yapabilir
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu işlemi yapma yetkiniz yok.")

    if request.method == "POST":
        images = request.FILES.getlist("images")
        if not images:
            messages.warning(request, "Herhangi bir dosya seçilmedi.")
            return redirect("order_detail", pk=pk)

        for file in images:
            try:
                OrderImage.objects.create(order=order, image=file)
            except Exception as e:
                print("⚠️ Görsel yükleme hatası:", e)
                messages.error(request, f"{file.name} yüklenemedi: {e}")

        messages.success(request, f"{len(images)} görsel başarıyla yüklendi ✅")
        return redirect("order_detail", pk=pk)

    return HttpResponseForbidden("Geçersiz istek yöntemi.")

@login_required
def delete_order_image(request, image_id):
    # 🛡️ Sadece patron veya müdür silebilir
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu işlemi yapma yetkiniz yok.")

    image = get_object_or_404(OrderImage, id=image_id)
    order_id = image.order.id

    # 🧹 Supabase tarafında da silmeyi istiyorsan (opsiyonel)
    try:
        from django.conf import settings
        from supabase import create_client
        import os

        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        filename = os.path.basename(image.image_url or "")
        if filename:
            supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).remove([filename])
    except Exception as e:
        print("⚠️ Supabase silme hatası:", e)

    # 🔸 Veritabanından kaydı sil
    image.delete()
    messages.success(request, "Görsel başarıyla silindi.")
    return redirect("order_detail", pk=order_id)


@login_required
def delete_order_event(request, event_id):
    event = get_object_or_404(OrderEvent, id=event_id)

    # 🛡️ Sadece patron veya müdür silebilir
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu işlemi yapma yetkiniz yok.")

    order_id = event.order.id
    event.delete()

    messages.success(request, "Üretim geçmişi kaydı silindi.")
    return redirect("order_detail", pk=order_id)


@login_required
@csrf_exempt
def order_delete(request, pk):

    # 🛡️ YETKİ KONTROLÜ
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return JsonResponse({"status": "error", "message": "Yetki yok"}, status=403)

    # 🛠️ SİLME
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        order.delete()
        return JsonResponse({"status": "ok"}, status=200)

    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)



# 📊 GENEL ÜRETİM RAPORU
@login_required
def reports_view(request):
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")
    gorev_filter = request.GET.get("gorev")

    events = OrderEvent.objects.select_related("order").all()

    if start_date:
        events = events.filter(timestamp__date__gte=start_date)
    if end_date:
        events = events.filter(timestamp__date__lte=end_date)
    if gorev_filter:
        events = events.filter(gorev=gorev_filter)

    stage_summary = (
        events.values("stage", "value")
        .annotate(count=Count("id"))
        .order_by("stage")
    )

    user_summary = (
        events.values("user", "gorev")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    context = {
        "stage_summary": stage_summary,
        "user_summary": user_summary,
        "start_date": start_date or "",
        "end_date": end_date or "",
        "gorev_filter": gorev_filter or "",
        "GOREVLER": UserProfile.GOREV_SECENEKLERI,
    }

    return render(request, "reports/general_reports.html", context)


# 📦 GİDEN ÜRÜNLER RAPORU (yeni versiyon)
@login_required
def giden_urunler_raporu(request):
    # Sadece patron veya müdür görebilir
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu raporu görme yetkiniz yok.")

    orders = list(
    Order.objects
    .filter(sevkiyat_durum="gonderildi")
    .select_related("musteri")
    .order_by("-id")
)


    # Toplam kar hesaplama
    toplam_kar = sum([o.kar or 0 for o in orders if o.kar is not None])
    toplam_satis = sum([o.satis_fiyati or 0 for o in orders if o.satis_fiyati is not None])
    toplam_maliyet = sum([o.efektif_maliyet or 0 for o in orders if o.efektif_maliyet is not None])

    context = {
        "orders": orders,
        "toplam_kar": toplam_kar,
        "toplam_satis": toplam_satis,
        "toplam_maliyet": toplam_maliyet,
    }

    return render(request, "reports/giden_urunler.html", context)


# 👥 Kullanıcı Yönetimi
@login_required
def user_management_view(request):
    # 🛡️ Sadece patron ve müdür erişebilsin
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu sayfaya erişim yetkiniz yok.")
        
    from django.contrib import messages
    from django.contrib.auth.models import Group, User

    users = User.objects.all().order_by("username")
    profiles = {p.user_id: p for p in UserProfile.objects.filter(user__in=users)}

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "create_user":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "").strip()
            role = request.POST.get("role", "").strip()
            gorev = request.POST.get("gorev", "yok").strip()

            if not username or not password or not role:
                messages.error(request, "Kullanıcı adı, şifre ve rol zorunludur.")
                return redirect("user_management")

            if User.objects.filter(username=username).exists():
                messages.warning(request, f"{username} zaten mevcut ⏸️")
                return redirect("user_management")

            user = User.objects.create_user(username=username, password=password)
            if role in ["personel", "mudur", "patron"]:
                group, _ = Group.objects.get_or_create(name=role)
                user.groups.add(group)

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.gorev = gorev
            profile.save()

            messages.success(request, f"{username} eklendi ✅")
            return redirect("user_management")

        elif action == "reset_password":
            user_id = request.POST.get("user_id")
            new_password = request.POST.get("new_password", "").strip()
            try:
                u = User.objects.get(pk=user_id)
                if not new_password:
                    messages.error(request, "Yeni şifre boş olamaz.")
                else:
                    u.set_password(new_password)
                    u.save()
                    messages.success(request, f"{u.username} için şifre güncellendi 🔐")
            except User.DoesNotExist:
                messages.error(request, "Kullanıcı bulunamadı.")
            return redirect("user_management")

        elif action == "update_gorev":
            user_id = request.POST.get("user_id")
            gorev = request.POST.get("gorev", "yok").strip()
            try:
                u = User.objects.get(pk=user_id)
                profile, _ = UserProfile.objects.get_or_create(user=u)
                profile.gorev = gorev
                profile.save()
                messages.success(request, f"{u.username} görevi '{profile.gorev}' olarak güncellendi 🏷️")
            except User.DoesNotExist:
                messages.error(request, "Kullanıcı bulunamadı.")
            return redirect("user_management")

        elif action == "delete_user":
            user_id = request.POST.get("user_id")
            try:
                u = User.objects.get(pk=user_id)
                if u == request.user:
                    messages.warning(request, "Kendinizi silemezsiniz.")
                else:
                    u.delete()
                    messages.success(request, "Kullanıcı silindi 🗑️")
            except User.DoesNotExist:
                messages.error(request, "Silinecek kullanıcı bulunamadı.")
            return redirect("user_management")

    context = {
        "users": users,
        "profiles": profiles,
        "GOREVLER": UserProfile.GOREV_SECENEKLERI,
    }
    return render(request, "user_management.html", context)


@login_required
def staff_reports_view(request):
    users = User.objects.all()
    selected_user = request.GET.get("user")
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")

    events = []

    # Sadece filtreleme yapılmışsa verileri getir
    if selected_user and start_date and end_date:
        try:
            user = User.objects.get(username=selected_user)
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

            events = (
                OrderEvent.objects.filter(
                    user=user,
                    timestamp__range=[start, end]
                )
                .select_related("order", "order__musteri")
                .order_by("-timestamp")
            )
        except User.DoesNotExist:
            pass

    context = {
        "users": users,
        "events": events,
        "selected_user": selected_user,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "reports/staff_reports.html", context)



from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from core.models import Order

from decimal import Decimal
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce

@login_required
@never_cache
def fast_profit_report(request):

    # 🛡️ Yetki kontrolü
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu sayfaya erişim yetkiniz yok.")

    musteri = request.GET.get("musteri", "").strip()
    tarih1 = request.GET.get("t1")
    tarih2 = request.GET.get("t2")

    orders = (
        Order.objects
        .select_related("musteri")
        .filter(sevkiyat_durum="gonderildi")
        .order_by("-id")
    )

    # ---- Filtreler ----
    if musteri:
        orders = orders.filter(musteri__ad__icontains=musteri)

    if tarih1 and tarih2:
        orders = orders.filter(siparis_tarihi__range=[tarih1, tarih2])
    elif tarih1:
        orders = orders.filter(siparis_tarihi__gte=tarih1)
    elif tarih2:
        orders = orders.filter(siparis_tarihi__lte=tarih2)

    # ----------------------------------------------------
    # 🛠️ TİP GÜVENLİ MALİYET HESABI
    # ----------------------------------------------------
    DEC = DecimalField(max_digits=12, decimal_places=2)
    ZERO = Decimal("0.00")

    maliyet_expr = ExpressionWrapper(
        Coalesce(F("maliyet_override"), ZERO, output_field=DEC)
        + Coalesce(F("maliyet_uygulanan"), ZERO, output_field=DEC)
        + Coalesce(F("ekstra_maliyet"), ZERO, output_field=DEC),
        output_field=DEC,
    )

    # ----------------------------------------------------
    # ⚡ TOPLAM HESAPLAMA
    # ----------------------------------------------------
    agg = orders.aggregate(
        toplam_ciro=Coalesce(Sum("satis_fiyati", output_field=DEC), ZERO, output_field=DEC),
        toplam_maliyet=Coalesce(Sum(maliyet_expr, output_field=DEC), ZERO, output_field=DEC),
    )

    toplam_ciro = agg["toplam_ciro"]
    toplam_maliyet = agg["toplam_maliyet"]
    toplam_kar = toplam_ciro - toplam_maliyet

    # ---- Sayfalama ----
    paginator = Paginator(orders, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "toplam_ciro": toplam_ciro,
        "toplam_maliyet": toplam_maliyet,
        "toplam_kar": toplam_kar,
        "musteri": musteri or "",
    }

    response = render(request, "reports/fast_profit_report.html", context)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response




# 🧾 ÜRÜN MALİYET LİSTESİ YÖNETİMİ
@login_required
def product_cost_list(request):
    # Sadece patron veya müdür erişebilir
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu sayfaya erişim yetkiniz yok.")

    # 🧩 Yeni kayıt ekleme veya silme işlemleri
    if request.method == "POST":
        action = request.POST.get("action")

        # ➕ Yeni kayıt ekle veya güncelle
        if action == "add":
            urun_kodu = request.POST.get("urun_kodu", "").strip()
            maliyet = request.POST.get("maliyet", "").strip()
            para_birimi = request.POST.get("para_birimi", "TRY")

            if urun_kodu and maliyet:
                ProductCost.objects.update_or_create(
                    urun_kodu=urun_kodu,
                    defaults={"maliyet": maliyet, "para_birimi": para_birimi},
                )

        # ❌ Silme işlemi
        elif action == "delete":
            pk = request.POST.get("id")
            ProductCost.objects.filter(id=pk).delete()

    # 📋 Listele (sayfalama ile)
    maliyetler = ProductCost.objects.all().order_by("urun_kodu")
    paginator = Paginator(maliyetler, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "costs/product_cost_list.html", {"costs": page_obj})

# 🧭 Yönetim Paneli
@login_required
def management_panel(request):
    # Kullanıcı rolünü kontrol et (sadece patron veya müdür erişebilir)
    user_groups = list(request.user.groups.values_list("name", flat=True))
    user_is_manager = any(role in user_groups for role in ["patron", "mudur"])

    # Eğer kullanıcı müdür veya patron değilse, order_list sayfasına yönlendir
    if not user_is_manager:
        return redirect("order_list")

    # 📅 Bugünün tarihini al
    today = timezone.now().date()

    # 🔹 Bugün yapılan işlemleri grupla (personel bazlı)
    events_today = (
        OrderEvent.objects.filter(timestamp__date=today)
        .values("user")
        .annotate(total=Count("id"), last_time=Max("timestamp"))
        .order_by("-total")
    )

    # 🔹 Kullanıcı görev bilgilerini al
    user_profiles = {p.user.username: p.gorev for p in UserProfile.objects.all()}

    # 🔹 Yetki durumunu şablona gönder
    context = {
        "events_today": events_today,
        "user_profiles": user_profiles,
        "today": today,
        "user_is_manager": user_is_manager,  # <-- burası yeni eklendi
    }

    # Yönetim paneli sayfasını göster
    return render(request, "management_panel.html", context)


# 📊 RAPORLAR ANA SAYFASI (Raporlara Git →)
@login_required
def reports_home(request):
    # Sadece patron veya müdür görebilsin
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu sayfaya erişim yetkiniz yok.")
    
    # reports/reports_home.html şablonunu render et
    return render(request, "reports/reports_home.html")

# 💬 Asistan sayfası (HTML)
@login_required
def ai_assistant_view(request):
    return render(request, "core/asistan.html")


@csrf_exempt
def ai_assistant_api(request):
    if request.method == "POST":
        try:
            import requests, os, json
            data = json.loads(request.body)
            user_message = data.get("message", "").strip()

            if not user_message:
                return JsonResponse({"reply": "❗Lütfen bir mesaj yazın."})

            GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
            if not GEMINI_API_KEY:
                return JsonResponse({"reply": "🔧 Asistan çevrimdışı (API anahtarı eksik)."})

            # ✅ Güncel model ve doğru endpoint
            MODEL = "gemini-2.5-flash"  # istersen gemini-2.5-pro ile değiştir
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_API_KEY}"

            payload = {
                "contents": [
                    {"parts": [{"text": user_message}]}
                ]
            }
            headers = {"Content-Type": "application/json"}

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            result = response.json()

            if "candidates" in result and len(result["candidates"]) > 0:
                reply = result["candidates"][0]["content"]["parts"][0]["text"]
            elif "error" in result:
                reply = f"⚠️ API Hatası: {result['error'].get('message', 'Bilinmeyen hata')}"
            else:
                reply = f"⚠️ Beklenmeyen yanıt: {result}"

        except Exception as e:
            reply = f"⚠️ Bir hata oluştu: {str(e)}"

        return JsonResponse({"reply": reply})

    # GET isteklerine basit bir yanıt dön
    return JsonResponse({"reply": "Bu endpoint sadece POST isteklerini kabul eder."})

@login_required
def fasoncu_ekle(request):
    if request.method == "POST":
        ad = request.POST.get("ad")
        telefon = request.POST.get("telefon")
        notlar = request.POST.get("notlar")

        if ad:
            Fasoncu.objects.create(ad=ad, telefon=telefon, notlar=notlar)
            messages.success(request, f"{ad} başarıyla eklendi.")
            return redirect("/reports/fasoncu/")
        else:
            messages.error(request, "Fasoncu adı boş bırakılamaz.")
    return render(request, "fasoncu_ekle.html")

@login_required
def fasoncu_raporu(request):
    from django.db.models import Q

    # 🔹 Tüm fasoncuları filtre dropdown için al
    fasoncular = Fasoncu.objects.all().order_by("ad")

    # 🔹 Seçili fasoncu ve tarih aralıklarını al
    fasoncu_id = request.GET.get("fasoncu")
    t1 = request.GET.get("t1")
    t2 = request.GET.get("t2")

    # 🔹 OrderEvent’lerden filtreye göre çekim
    raporlar = OrderEvent.objects.select_related("order", "order__musteri", "fasoncu")

    # Eğer belirli fasoncu seçildiyse
    if fasoncu_id:
        raporlar = raporlar.filter(fasoncu_id=fasoncu_id)

    # Eğer tarih aralığı varsa uygula
    if t1 and t2:
        raporlar = raporlar.filter(timestamp__range=[t1, t2])
    elif t1:
        raporlar = raporlar.filter(timestamp__date__gte=t1)
    elif t2:
        raporlar = raporlar.filter(timestamp__date__lte=t2)

    # 🔹 Yalnızca fasonla ilgili event'leri göster (örnek: fasona verildi / alındı)
    raporlar = raporlar.filter(
        Q(stage__icontains="fason")  # "dikim_fason_durumu" veya "susleme_fason_durumu"
    ).order_by("-timestamp")

    # 🔹 Görsel veriler için küçük context hazırlama
    data = []
    for r in raporlar:
        data.append({
            "order": r.order,
            "durum": f"{r.stage.replace('_', ' ').title()} → {r.value.title()}",
            "tarih": r.timestamp,
            "personel": r.user,
        })

    context = {
        "fasoncular": fasoncular,
        "raporlar": data,
    }
    return render(request, "reports/fasoncu_raporu.html", context)

@login_required
def fasoncu_yeni(request):
    if request.method == "POST":
        ad = request.POST.get("ad")
        telefon = request.POST.get("telefon")
        notlar = request.POST.get("notlar")

        if ad:
            Fasoncu.objects.create(ad=ad, telefon=telefon, notlar=notlar, eklenme_tarihi=timezone.now())
            messages.success(request, "Yeni fasoncu başarıyla eklendi.")
            return redirect("/reports/fasoncu/")
        else:
            messages.error(request, "Fasoncu adı zorunludur.")

    return render(request, "fasoncu_yeni.html")



@login_required
def nakisci_raporu(request):
    from django.db.models import Q

    # 🔹 Tüm nakışçıları filtre dropdown için al
    nakiscilar = Nakisci.objects.all().order_by("ad")

    # 🔹 Seçili nakışçı ve tarih aralıklarını al
    nakisci_id = request.GET.get("nakisci")
    t1 = request.GET.get("t1")
    t2 = request.GET.get("t2")

    # 🔹 OrderEvent’lerden filtreye göre çekim
    raporlar = OrderEvent.objects.select_related("order", "order__musteri", "nakisci")

    # Eğer belirli nakışçı seçildiyse
    if nakisci_id:
        raporlar = raporlar.filter(nakisci_id=nakisci_id)

    # Eğer tarih aralığı varsa uygula
    if t1 and t2:
        raporlar = raporlar.filter(timestamp__range=[t1, t2])
    elif t1:
        raporlar = raporlar.filter(timestamp__date__gte=t1)
    elif t2:
        raporlar = raporlar.filter(timestamp__date__lte=t2)

    # 🔹 Yalnızca nakış ile ilgili event’leri göster (örnek: nakışa verildi / alındı)
    raporlar = raporlar.filter(
        Q(stage__icontains="nakis") | Q(stage__icontains="nakış")
    ).order_by("-timestamp")

    # 🔹 Görsel veriler için context hazırlama
    data = []
    for r in raporlar:
        data.append({
            "order": r.order,
            "durum": f"{r.stage.replace('_', ' ').title()} → {r.value.title()}",
            "tarih": r.timestamp,
            "personel": r.user,
        })

    context = {
        "nakiscilar": nakiscilar,
        "raporlar": data,
    }
    return render(request, "reports/nakisci_raporu.html", context)




@login_required
def nakisci_ekle(request):
    if request.method == 'POST':
        ad = request.POST.get('ad', '').strip()
        telefon = request.POST.get('telefon', '').strip()
        notlar = request.POST.get('notlar', '').strip()
        if ad:
            Nakisci.objects.create(ad=ad, telefon=telefon, notlar=notlar)
            return redirect('nakisci_raporu')  # veya '/reports/nakisci/'
    return render(request, 'nakisci/yeni.html')

from django.db.models import F, Sum

@login_required
def depo_detay(request, depo_adi):

    stoklar = (
        DepoStok.objects
        .filter(depo=depo_adi)
        .select_related("order")
        .annotate(
            order_siparis_no=F("order__siparis_numarasi"),
            order_tipi=F("order__siparis_tipi"),
            order_musteri=F("order__musteri"),
            order_siparis_tarihi=F("order__siparis_tarihi"),
            order_teslim_tarihi=F("order__teslim_tarihi"),
        )
        .order_by("-eklenme_tarihi")
    )

    toplam_adet = stoklar.aggregate(Sum("adet"))["adet__sum"] or 0
    siparisler = Order.objects.all().order_by("-siparis_tarihi")

    return render(request, "depolar/detay.html", {
        "depo_adi": depo_adi,
        "stoklar": stoklar,
        "toplam_adet": toplam_adet,
        "siparisler": siparisler,
    })









@login_required
def depo_arama(request):
    # 🔍 Filtre parametreleri
    urun_kodu = request.GET.get("urun_kodu", "").strip()
    renk = request.GET.get("renk", "")
    beden = request.GET.get("beden", "")
    depo = request.GET.get("depo", "")

    # 🧮 Filtre oluştur
    filtre = Q()
    if urun_kodu:
        filtre &= Q(urun_kodu__icontains=urun_kodu)
    if renk:
        filtre &= Q(renk=renk)
    if beden:
        filtre &= Q(beden=beden)
    if depo:
        filtre &= Q(depo=depo)

    # 📦 Sorgu
    stoklar = []
    if any([urun_kodu, renk, beden, depo]):
        stoklar = (
            DepoStok.objects
            .filter(filtre)
            .select_related("order")  # 🔗 Sipariş ilişkisini getir
            .values(
                "depo",
                "urun_kodu",
                "renk",
                "beden",
                "order__id",
                "order__siparis_numarasi"
            )
            .annotate(toplam_adet=Sum("adet"))
            .order_by("depo", "urun_kodu")
        )

    # 🔽 Dropdown listeleri dinamik olarak çek
    renk_listesi = (
        DepoStok.objects.exclude(renk__isnull=True)
        .values_list("renk", flat=True).distinct().order_by("renk")
    )
    beden_listesi = (
        DepoStok.objects.exclude(beden__isnull=True)
        .values_list("beden", flat=True).distinct().order_by("beden")
    )
    depo_listesi = (
        DepoStok.objects.exclude(depo__isnull=True)
        .values_list("depo", flat=True).distinct().order_by("depo")
    )
    urun_listesi = (
        DepoStok.objects.exclude(urun_kodu__isnull=True)
        .values_list("urun_kodu", flat=True).distinct().order_by("urun_kodu")
    )

    context = {
        "stoklar": stoklar,
        "renk_listesi": renk_listesi,
        "beden_listesi": beden_listesi,
        "depo_listesi": depo_listesi,
        "urun_listesi": urun_listesi,
        "request": request,
    }
    return render(request, "depolar/arama.html", context)



@login_required
def hazirdan_ver(request, stok_id):
    stok = get_object_or_404(DepoStok, id=stok_id)

    if request.method == "POST":
        order_id = request.POST.get("order_id")
        hedef_order = get_object_or_404(Order, id=order_id)

        # 🔻 Stoktan 1 adet düş
        stok.adet = max(0, stok.adet - 1)

        # 🔻 STOĞA ÜRETİM siparişi (kaynak sipariş)
        kaynak_order = stok.order  

        # 🔻 Ürünü hedef siparişe aktar
        stok.order = hedef_order
        stok.save()

        # 🔹 Aynı siparişe ait önceki stok kayıtlarını temizle
        DepoStok.objects.filter(order=hedef_order).exclude(id=stok.id).delete()

        # ============================================================
        # 1) Kaynak sipariş için üretim geçmişi kaydı
        # ============================================================
        if kaynak_order:
            UretimGecmisi.objects.create(
                order=kaynak_order,
                urun=stok.urun_kodu,
                asama="Hazırdan Verildi",
                aciklama=f"Bu ürün {hedef_order.siparis_numarasi} siparişine gönderildi.",
            )

            # 🔥 OrderEvent (Order Detail'de görünmesi için)
            OrderEvent.objects.create(
                order=kaynak_order,
                user=request.user.username,
                gorev="hazir",
                stage="Hazırdan Verildi",
                value=f"{stok.urun_kodu} → {hedef_order.siparis_numarasi}",
                adet=1,
                event_type="stage",
            )

        # ============================================================
        # 2) Hedef sipariş için üretim geçmişi kaydı
        # ============================================================
        UretimGecmisi.objects.create(
            order=hedef_order,
            urun=stok.urun_kodu,
            asama="Depodan Teslim Alındı",
            aciklama=f"Bu ürün depodan alındı. Kaynak Sipariş: {kaynak_order.siparis_numarasi if kaynak_order else '-'}",
        )

        # 🔥 OrderEvent (Order Detail'de görünmesi için)
        OrderEvent.objects.create(
            order=hedef_order,
            user=request.user.username,
            gorev="hazir",
            stage="Depodan Teslim Alındı",
            value=stok.urun_kodu,
            adet=1,
            event_type="stage",
        )

        # ✔️ Kullanıcıya bildirim
        messages.success(
            request,
            f"{stok.urun_kodu} → {hedef_order.siparis_numarasi} siparişine başarıyla teslim edildi."
        )

        return redirect("depo_detay", depo_adi=stok.depo)

    # GET isteğinde sipariş listesi göster
    siparisler = Order.objects.all().order_by("-id")

    return render(request, "depolar/hazirdan_ver.html", {
        "stok": stok,
        "siparisler": siparisler,
    })



# AJAX ile müşteri ekleme
@login_required
def musteri_create_ajax(request):
    if request.method == "POST":
        ad = request.POST.get("ad", "").strip()
        telefon = request.POST.get("telefon", "").strip()

        if not ad:
            return JsonResponse({"success": False, "message": "Müşteri adı zorunludur."})

        m = Musteri.objects.create(ad=ad, telefon=telefon)

        return JsonResponse({
            "success": True,
            "id": m.id,
            "ad": m.ad
        })

    return JsonResponse({"success": False, "message": "Geçersiz istek"})

@login_required
def cikti_alindi(request, pk):
    """
    Siparişin 'Yazdırıldı / Çıktı Alındı' şeklinde işaretlenmesi.
    """
    order = get_object_or_404(Order, id=pk)
    order.cikti_alindi = True
    order.save(update_fields=["cikti_alindi"])

    messages.success(request, f"{order.siparis_numarasi} yazdırıldı olarak işaretlendi.")
    return redirect("order_detail", pk=pk)



@csrf_exempt
def ajax_musteri_ekle(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Geçersiz istek yöntemi."})

    ad = request.POST.get("ad", "").strip()

    if not ad:
        return JsonResponse({"success": False, "message": "Müşteri adı boş olamaz."})

    # Müşteri oluştur
    musteri = Musteri.objects.create(ad=ad)

    return JsonResponse({
        "success": True,
        "id": musteri.id,
        "ad": musteri.ad
    })

@require_POST
def musteri_pasif_yap_ajax(request):
    musteri_id = request.POST.get("id")

    if not musteri_id:
        return JsonResponse({"success": False, "message": "Müşteri ID bulunamadı."})

    try:
        musteri = Musteri.objects.get(id=musteri_id)
        musteri.aktif = False
        musteri.save()

        return JsonResponse({
            "success": True,
            "message": "Müşteri pasif yapıldı.",
            "id": musteri.id
        })

    except Musteri.DoesNotExist:
        return JsonResponse({"success": False, "message": "Müşteri bulunamadı."})


def stok_ekle(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        depo = request.POST.get("depo")
        adet = int(request.POST.get("adet", 0))

        if not depo or adet <= 0:
            messages.error(request, "Lütfen depo ve adet bilgilerini doğru girin.")
            return redirect("order_detail", pk=order.id)

        # ✔️ 1) Eski depodaki stok kaydını tamamen sil
        DepoStok.objects.filter(order=order).delete()

        # ✔️ 2) Yeni depo kaydı oluştur
        DepoStok.objects.create(
            urun_kodu=order.urun_kodu,
            renk=order.renk,
            beden=order.beden,
            adet=adet,
            depo=depo,
            aciklama=f"Stoğa Üretim: {order.siparis_numarasi}",
            order=order
        )

        # ✔️ 3) Üretim geçmişine kayıt gir
        OrderEvent.objects.create(
            order=order,
            user=request.user.username,
            gorev="hazir",
            stage="Depoya Aktarım",
            value=f"{adet} adet stoğa eklendi ({depo})",
            adet=adet,
            timestamp=timezone.now(),
        )

        messages.success(request, f"✅ {adet} adet ürün {depo} deposuna eklendi.")
        return redirect("order_detail", pk=order.id)



# 📌 Sipariş düzenleme değişikliklerini loglayan fonksiyon
def log_order_updates(request, old_obj, new_obj):
    from .models import OrderEvent

    changed = []

    # 📌 Takip edilecek alanlar
    fields = [
        "musteri", "siparis_tipi", "urun_kodu", "renk", "beden",
        "adet", "siparis_tarihi", "teslim_tarihi",
        "aciklama", "musteri_referans"
    ]

    for field in fields:
        old_val = getattr(old_obj, field, None)
        new_val = getattr(new_obj, field, None)

        # Müşteri gibi FK alanları ad ile yazalım
        if hasattr(old_val, "ad"):
            old_val = old_val.ad
        if hasattr(new_val, "ad"):
            new_val = new_val.ad

        if old_val != new_val:
            changed.append((field, old_val, new_val))

    # Her değişikliği OrderEvent olarak kaydet
    for field, old, new in changed:
        OrderEvent.objects.create(
            order=new_obj,
            user=request.user.username,
            gorev="yok",
            event_type="order_update",
            stage=field,
            value=f"{field} güncellendi",
            old_value=str(old),
            new_value=str(new)
        )


@login_required
def notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()

    # Sipariş varsa sipariş detayına yönlendir
    if notif.order:
        return redirect("order_detail", pk=notif.order.id)

    # Sipariş yoksa bildirim listesine dön
    return redirect("notification_list")

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-timestamp")
    return render(request, "core/notification_list.html", {"notifications": notifications})

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from .models import Notification

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, "notifications/list.html", {"notifications": notifications})


from django.shortcuts import get_object_or_404, redirect
from .models import Notification

@login_required
def mark_notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()

    # Eğer bildirim siparişe bağlıysa sipariş detayına yönlendir
    if notif.order:
        return redirect("order_detail", pk=notif.order.id)

    # Değilse bildirim listesine dön
    return redirect("notification_list")


@login_required
def order_multi_create(request):
    if request.method == "POST":

        urun_kodu = request.POST.get("urun_kodu")
        musteri_id = request.POST.get("musteri")
        siparis_tipi = request.POST.get("siparis_tipi") or None
        teslim_tarihi = request.POST.get("teslim_tarihi") or None
        aciklama = request.POST.get("aciklama")

        musteri = Musteri.objects.filter(id=musteri_id).first()

        created_orders = []

        # 🔍 Gönderilen tüm POST anahtarlarını al
        post_keys = request.POST.keys()

        # 🔢 Kaç satır olduğunu otomatik bulmak için:
        row_indices = set()

        for key in post_keys:
            if key.startswith("renk_row_"):
                index = key.replace("renk_row_", "")
                row_indices.add(int(index))

        # 🧮 Her satırı sırayla işle
        for i in sorted(row_indices):

            renk = request.POST.get(f"renk_row_{i}")
            bedenler = request.POST.getlist(f"beden_row_{i}[]")

            if not renk:
                continue

            if not bedenler:
                continue

            # Her beden için ayrı sipariş oluştur
            for beden in bedenler:

                order = Order.objects.create(
                    siparis_tipi=siparis_tipi,        # SERI veya STOK
                    musteri=musteri,
                    urun_kodu=urun_kodu,
                    renk=renk,
                    beden=beden,
                    adet=1,
                    teslim_tarihi=teslim_tarihi or None,
                    aciklama=aciklama,
                )

                created_orders.append(order)

        messages.success(request, f"{len(created_orders)} adet sipariş başarıyla oluşturuldu!")
        return redirect("order_list")

    # GET → Formu göster
    context = {
        "musteriler": Musteri.objects.filter(aktif=True),
        "renkler": Order.objects.values_list("renk", flat=True).distinct(),
        "bedenler": Order.objects.values_list("beden", flat=True).distinct(),
    }
    return render(request, "core/order_multi_create.html", context)



