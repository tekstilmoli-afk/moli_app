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
    close_old_connections()  # ✅ Eski bağlantıları güvenli şekilde kapat
    # 🔧 Her sorgudan önce bağlantıyı sıfırla (cache kalmasın)
    connections["default"].close()

    # ✅ Türkçe açıklamalı durum sözlüğü
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

    # ✅ Her siparişin son event’ini tek sorguda al (timestamp + id sıralaması)
    latest_event = (
        OrderEvent.objects
        .filter(order=OuterRef("pk"))
        .order_by("-timestamp", "-id")
        .values("stage", "value")[:1]
    )

    # ✅ Ana sorgu
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

    # ✅ Filtreler
    siparis_nolar = request.GET.getlist("siparis_no")
    musteriler = request.GET.getlist("musteri")
    urun_kodlari = request.GET.getlist("urun_kodu")
    renkler = request.GET.getlist("renk")
    bedenler = request.GET.getlist("beden")
    status_filter = request.GET.getlist("status")

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

    if status_filter:
        stage_value_pairs = [
            key for key, val in STAGE_TRANSLATIONS.items() if val in status_filter
        ]
        query = Q()
        for stage, value in stage_value_pairs:
            query |= Q(latest_stage=stage, latest_value=value)
        qs = qs.filter(query)

    teslim_baslangic = request.GET.get("teslim_tarihi_baslangic")
    teslim_bitis = request.GET.get("teslim_tarihi_bitis")
    if teslim_baslangic and teslim_bitis:
        qs = qs.filter(teslim_tarihi__range=[teslim_baslangic, teslim_bitis])
    elif teslim_baslangic:
        qs = qs.filter(teslim_tarihi__gte=teslim_baslangic)
    elif teslim_bitis:
        qs = qs.filter(teslim_tarihi__lte=teslim_bitis)

    # ✅ Sayfalama
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    # ✅ Okunabilir son durum
    for order in page_obj:
        if order.latest_stage and order.latest_value:
            order.formatted_status = STAGE_TRANSLATIONS.get(
                (order.latest_stage, order.latest_value),
                f"{order.latest_stage.replace('_', ' ').title()} → {order.latest_value.title()}",
            )
        else:
            order.formatted_status = "-"

    # ✅ Filtre seçenekleri
    siparis_options = Order.objects.values_list("siparis_numarasi", flat=True).distinct()
    musteri_options = Order.objects.values_list("musteri__ad", flat=True).distinct()
    urun_options = Order.objects.values_list("urun_kodu", flat=True).distinct()
    renk_options = Order.objects.values_list("renk", flat=True).distinct()
    beden_options = Order.objects.values_list("beden", flat=True).distinct()
    status_options = list(set(STAGE_TRANSLATIONS.values()))

    context = {
        "orders": page_obj,
        "siparis_options": siparis_options,
        "musteri_options": musteri_options,
        "urun_options": urun_options,
        "renk_options": renk_options,
        "beden_options": beden_options,
        "status_options": status_options,
        "status_selected": status_filter,
        "siparis_no_selected": siparis_nolar,
        "musteri_selected": musteriler,
        "urun_kodu_selected": urun_kodlari,
        "renk_selected": renkler,
        "beden_selected": bedenler,
        "teslim_baslangic_selected": teslim_baslangic,
        "teslim_bitis_selected": teslim_bitis,
    }

    response = render(request, "core/order_list.html", context)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


# ➕ Yeni Sipariş
@login_required
def order_create(request):
    if request.method == "POST":
        form = OrderForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            order = form.save(commit=False)

            # 🧮 Ürün koduna göre otomatik maliyet ata
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

            # ✅ Cache temizle ve tarayıcı önbelleğini aş
            from django.core.cache import cache
            cache.clear()
            return redirect(f"{reverse('order_list')}?t={int(time.time())}")

    else:
        form = OrderForm(user=request.user)

    is_manager = request.user.groups.filter(name__in=["patron", "mudur"]).exists()

    return render(request, "core/order_form.html", {
        "form": form,
        "is_manager": is_manager,
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


# 📌 Sipariş Detay (Geçmiş Dahil)
@login_required
@never_cache
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("musteri"), pk=pk)
    nakisciler = Nakisci.objects.all()
    fasoncular = Fasoncu.objects.all()  # ✅ BUNU EKLEDİK
    events = OrderEvent.objects.filter(order=order).order_by("timestamp")

    is_manager = request.user.groups.filter(name__in=["patron", "mudur"]).exists()

    return render(
        request,
        "core/order_detail.html",
        {
            "order": order,
            "nakisciler": nakisciler,
            "fasoncular": fasoncular,  # ✅ BUNU DA EKLEDİK
            "events": events,
            "is_manager": is_manager,
        },
    )


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

    # 📌 Stage ve value bilgisi (zorunlu)
    stage = request.GET.get("stage") or request.POST.get("stage")
    value = request.GET.get("value") or request.POST.get("value")
    is_production_count = request.GET.get("is_production_count") or request.POST.get("is_production_count")

    if not stage or not value:
        return HttpResponseForbidden("Eksik veri")

    # 📌 Diğer alanlar (opsiyonel)
    aciklama = request.GET.get("aciklama") or request.POST.get("aciklama") or ""
    parca = request.GET.get("parca") or request.POST.get("parca") or ""
    adet_raw = request.GET.get("adet") or request.POST.get("adet")
    fasoncu_id = request.GET.get("fasoncu") or request.POST.get("fasoncu")

    # 📌 Adet boşsa 1 kabul edilir
    try:
        adet = int(adet_raw) if adet_raw else 1
    except:
        adet = 1

    # 📌 Kullanıcı ve görev bilgileri
    username = request.user.username
    gorev = getattr(request.user.userprofile, "gorev", "yok")
    now = timezone.now()

    # 📌 Eğer bu bir ProductionCount isteğiyse, farklı tabloya kaydet
    if is_production_count == "1":
        ProductionCount.objects.create(
            order=order,
            stage=stage,
            count=1,
            user=username,
            timestamp=now
        )
        return HttpResponse("OK")  # Eski panel yenilenmez

    # ✅ Fasoncu veya Nakışçı bilgisi varsa çek
    fasoncu = None
    nakisci = None
    if fasoncu_id:
        if stage == "nakis_durumu":
            nakisci = Nakisci.objects.filter(id=fasoncu_id).first()
        else:
            fasoncu = Fasoncu.objects.filter(id=fasoncu_id).first()

    # ✅ Normal süreç kaydı (OrderEvent)
    OrderEvent.objects.create(
        order=order,
        user=username,
        gorev=gorev,
        stage=stage,
        value=value,
        aciklama=aciklama,
        parca=parca,
        adet=adet,
        fasoncu=fasoncu,
        nakisci=nakisci,
        timestamp=now,
    )

    # 📌 Güncellenmiş paneli yeniden yükle
    order.refresh_from_db()
    events = OrderEvent.objects.filter(order=order).order_by("timestamp")
    html = render_to_string("core/_uretim_paneli.html", {"order": order, "events": events})
    return HttpResponse(html)



# ✅ Ürün resmi yüklemek / değiştirmek için fonksiyon
@login_required
def order_upload_image(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == "POST" and request.FILES.get("resim"):
        order.resim = request.FILES["resim"]
        order.save()

    return redirect("order_detail", pk=order.pk)

@login_required
def order_edit(request, pk):
    order = get_object_or_404(Order, pk=pk)

    # 🛡️ Yetki kontrolü
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu işlemi yapma yetkiniz yok.")

    if request.method == "POST":
        form = OrderForm(request.POST, request.FILES, instance=order, user=request.user)
        if form.is_valid():
            order = form.save()
            order.refresh_from_db()  # 🌀 Değişiklikleri anında yansıt
            print(f"✅ [DEBUG] Güncellendi: {order.id} - {order.siparis_numarasi}")

            # 🚀 Tarayıcı önbelleğini tamamen atlatmak için timestamp parametresi ekliyoruz
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
    # 🛡️ Yetki kontrolü — sadece patron veya müdür silebilir
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return JsonResponse({"success": False, "message": "🚫 Bu işlemi yapma yetkiniz yok."}, status=403)

    if request.method == "POST":
        try:
            order = get_object_or_404(Order, pk=pk)
            order.delete()

            # 🧹 Cache temizle
            cache.clear()

            return JsonResponse({"success": True, "message": "✅ Sipariş başarıyla silindi."}, status=200)

        except Exception as e:
            return JsonResponse({"success": False, "message": f"❌ Silme hatası: {str(e)}"}, status=500)

    return JsonResponse({"success": False, "message": "❌ Geçersiz istek yöntemi."}, status=405)


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



@login_required
def fast_profit_report(request):
    # 🛡️ Sadece patron ve müdür erişebilsin
    if not request.user.groups.filter(name__in=["patron", "mudur"]).exists():
        return HttpResponseForbidden("Bu sayfaya erişim yetkiniz yok.")

    from django.db.models import F, Sum, ExpressionWrapper, DecimalField, OuterRef, Subquery, Value
    from django.db.models.functions import Coalesce
    from datetime import datetime

    musteri = request.GET.get("musteri")
    tarih1 = request.GET.get("t1")
    tarih2 = request.GET.get("t2")

    # 🧠 Her siparişin en son event'ini al
    latest_event = OrderEvent.objects.filter(order=OuterRef("pk")).order_by("-timestamp")

    # 🔍 Sadece son event'i "sevkiyat_durum = gonderildi" olan siparişleri al
    orders = (
        Order.objects.select_related("musteri")
        .annotate(
            latest_stage=Subquery(latest_event.values("stage")[:1]),
            latest_value=Subquery(latest_event.values("value")[:1]),
        )
        .filter(latest_stage="sevkiyat_durum", latest_value="gonderildi")
    )

    # 🔸 Tarih ve müşteri filtreleri
    if musteri:
        orders = orders.filter(musteri__ad__icontains=musteri)
    if tarih1 and tarih2:
        try:
            t1 = datetime.strptime(tarih1, "%Y-%m-%d")
            t2 = datetime.strptime(tarih2, "%Y-%m-%d")
            orders = orders.filter(siparis_tarihi__range=[t1, t2])
        except ValueError:
            pass
    elif tarih1:
        orders = orders.filter(siparis_tarihi__gte=tarih1)
    elif tarih2:
        orders = orders.filter(siparis_tarihi__lte=tarih2)

    # 💰 Etkin maliyet & net kâr (kar property’siyle çakışmasın diye net_kar)
    eff_cost_expr = (
        Coalesce(F("maliyet_uygulanan"), Value(0, output_field=DecimalField()))
        + Coalesce(F("ekstra_maliyet"), Value(0, output_field=DecimalField()))
        + Coalesce(F("maliyet_override"), Value(0, output_field=DecimalField()))
    )

    orders = orders.annotate(
        ef_maliyet=ExpressionWrapper(
            eff_cost_expr, output_field=DecimalField(max_digits=15, decimal_places=2)
        ),
        net_kar=ExpressionWrapper(
            F("satis_fiyati") - eff_cost_expr, output_field=DecimalField(max_digits=15, decimal_places=2)
        ),
    )

    # 🔢 Toplamlar (ef_maliyet ve net_kar üzerinden)
    toplamlar = orders.aggregate(
        toplam_ciro=Coalesce(Sum("satis_fiyati", output_field=DecimalField()), Value(0, output_field=DecimalField())),
        toplam_maliyet=Coalesce(Sum("ef_maliyet", output_field=DecimalField()), Value(0, output_field=DecimalField())),
        toplam_kar=Coalesce(Sum("net_kar", output_field=DecimalField()), Value(0, output_field=DecimalField())),
    )

    # 📄 Sayfalama
    paginator = Paginator(orders.order_by("-id"), 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "toplam_ciro": toplamlar["toplam_ciro"],
        "toplam_maliyet": toplamlar["toplam_maliyet"],
        "toplam_kar": toplamlar["toplam_kar"],
        "musteri": musteri or "",
    }

    return render(request, "reports/fast_profit_report.html", context)













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
    if not any(role in user_groups for role in ["patron", "mudur"]):
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

    context = {
        "events_today": events_today,
        "user_profiles": user_profiles,
        "today": today,
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
