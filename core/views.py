from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Max, Count
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from openpyxl import Workbook

from .models import Order, Musteri, Nakisci, Fasoncu, OrderEvent, UserProfile
from .forms import OrderForm, MusteriForm


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


# 📋 Sipariş Listeleme
@login_required
def order_list(request):
    qs = (
        Order.objects.select_related("musteri")
        .only(
            "id",
            "siparis_numarasi",
            "siparis_tipi",
            "urun_kodu",
            "renk",
            "beden",
            "adet",
            "siparis_tarihi",
            "teslim_tarihi",
            "aciklama",
            "musteri__ad",
            "qr_code_url",
            "resim",
        )
    )

    # ✅ Modal üzerinden gelen çoklu filtre parametreleri
    siparis_nolar = request.GET.getlist("siparis_no")
    musteriler = request.GET.getlist("musteri")
    urun_kodlari = request.GET.getlist("urun_kodu")
    renkler = request.GET.getlist("renk")
    bedenler = request.GET.getlist("beden")
    status_filter = request.GET.getlist("status")

    # ✅ Filtreler uygulanıyor (seçilmişse)
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

    # ✅ Üretim Durumu Filtresi - OrderEvent üzerinden
    # ✅ STAGE_TRANSLATIONS sözlüğü burada önceden tanımlı değilse alta taşınacak
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

    if status_filter:
        stage_value_pairs = [
            key for key, val in STAGE_TRANSLATIONS.items() if val in status_filter
    ]
    
        # Geçici liste: sadece latest_event'i eşleşen siparişleri topla
        matching_ids = []
        for order in qs:
            latest_event = OrderEvent.objects.filter(order=order).order_by("-timestamp").first()
            if latest_event and (latest_event.stage, latest_event.value) in stage_value_pairs:
                matching_ids.append(order.id)

        qs = qs.filter(id__in=matching_ids)


        # Çoklu OR için Q nesneleri oluştur
        query = Q()
        for stage, value in stage_value_pairs:
            query |= Q(stage=stage, value=value)

        # Bu event'lere sahip sipariş ID'lerini al
        matching_order_ids = OrderEvent.objects.filter(query).values_list("order_id", flat=True)

        # Ana queryset'i bu orderlarla kısıtla
        qs = qs.filter(id__in=matching_order_ids)

    # ✅ Teslim Tarihi Aralığı Filtresi
    teslim_baslangic = request.GET.get("teslim_tarihi_baslangic")
    teslim_bitis = request.GET.get("teslim_tarihi_bitis")

    if teslim_baslangic and teslim_bitis:
        qs = qs.filter(teslim_tarihi__range=[teslim_baslangic, teslim_bitis])
    elif teslim_baslangic:
        qs = qs.filter(teslim_tarihi__gte=teslim_baslangic)
    elif teslim_bitis:
        qs = qs.filter(teslim_tarihi__lte=teslim_bitis)

    # ✅ Ek filtre yapısını çalıştır
    qs = apply_filters(request, qs)

    # ✅ Eğer sıralama yoksa default ver
    if not qs.query.order_by:
        qs = qs.order_by("-id")

    paginator = Paginator(qs, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # ✅ Üretim geçmişini (formatted_status) oluştur
    for order in page_obj:
        latest_event = OrderEvent.objects.filter(order=order).order_by("-timestamp").first()
        order.last_event = latest_event

        if latest_event:
            order.formatted_status = STAGE_TRANSLATIONS.get(
                (latest_event.stage, latest_event.value),
                f"{latest_event.stage.replace('_', ' ').title()} → {latest_event.value.title()}"
            )
        else:
            order.formatted_status = "-"

    # ✅ Modal seçenekleri (distinct verilerle)
    siparis_options = Order.objects.order_by().values_list("siparis_numarasi", flat=True).distinct()
    musteri_options = Order.objects.order_by().values_list("musteri__ad", flat=True).distinct()
    urun_options = Order.objects.order_by().values_list("urun_kodu", flat=True).distinct()
    renk_options = Order.objects.order_by().values_list("renk", flat=True).distinct()
    beden_options = Order.objects.order_by().values_list("beden", flat=True).distinct()
    status_options = list(set(STAGE_TRANSLATIONS.values()))

    context = {
        "orders": page_obj,
        "siparis_options": siparis_options,
        "musteri_options": musteri_options,
        "urun_options": urun_options,
        "renk_options": renk_options,
        "beden_options": beden_options,
        "siparis_no_selected": siparis_nolar,
        "musteri_selected": musteriler,
        "urun_kodu_selected": urun_kodlari,
        "renk_selected": renkler,
        "beden_selected": bedenler,
        "teslim_baslangic_selected": teslim_baslangic,
        "teslim_bitis_selected": teslim_bitis,
        "status_options": status_options,
        "status_selected": status_filter,
    }

    return render(request, "core/order_list.html", context)









# ➕ Yeni Sipariş
@login_required
def order_create(request):
    if request.method == "POST":
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("order_list")
    else:
        form = OrderForm()
    return render(request, "core/order_form.html", {"form": form})


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
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("musteri"), pk=pk)
    nakisciler = Nakisci.objects.all()
    fasoncular = Fasoncu.objects.all()  # ✅ BUNU EKLEDİK
    events = OrderEvent.objects.filter(order=order).order_by("timestamp")

    return render(
        request,
        "core/order_detail.html",
        {
            "order": order,
            "nakisciler": nakisciler,
            "fasoncular": fasoncular,  # ✅ BUNU DA EKLEDİK
            "events": events,
        },
    )


# 🔐 Özel Login
@csrf_exempt
def custom_login(request):
    if request.method == "POST":
        password = request.POST.get("password", "").strip()
        from django.contrib.auth.models import User

        users = User.objects.all()
        authenticated_user = None

        for u in users:
            user = authenticate(username=u.username, password=password)
            if user:
                authenticated_user = user
                break

        if authenticated_user:
            login(request, authenticated_user)
            user_groups = list(authenticated_user.groups.values_list("name", flat=True))
            next_url = request.GET.get("next", "/")

            if next_url and next_url not in ["/", "/management/"]:
                return redirect(next_url)

            if any(role in user_groups for role in ["patron", "mudur"]):
                return redirect("/management/")
            else:
                return redirect("/")

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




# 🗑️ Sipariş Silme
@login_required
def order_delete(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("Bu işlemi yapma yetkiniz yok.")
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        order.delete()
        return HttpResponse(status=204)
    return HttpResponse(status=405)


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

# 👥 Kullanıcı Yönetimi
@login_required
def user_management_view(request):
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


# 👷 PERSONEL ÇALIŞMA RAPORU
@login_required
def staff_reports_view(request):
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")
    gorev_filter = request.GET.get("gorev")

    events = OrderEvent.objects.all()

    if start_date:
        events = events.filter(timestamp__date__gte=start_date)
    if end_date:
        events = events.filter(timestamp__date__lte=end_date)
    if gorev_filter:
        events = events.filter(gorev=gorev_filter)

    staff_summary = (
        events.values("user")
        .annotate(total_events=Count("id"), last_activity=Max("timestamp"))
        .order_by("-total_events")
    )

    user_profiles = UserProfile.objects.select_related("user").all()
    user_to_gorev = {up.user.username: up.gorev for up in user_profiles}

    stage_data = {}
    for e in events:
        username = e.user
        stage = e.stage or "-"
        if username not in stage_data:
            stage_data[username] = {}
        stage_data[username][stage] = stage_data[username].get(stage, 0) + 1

    stage_data_display = {
        user: [{"stage": s, "count": c} for s, c in stages.items()]
        for user, stages in stage_data.items()
    }

    context = {
        "staff_summary": staff_summary,
        "stage_data": stage_data_display,
        "user_to_gorev": user_to_gorev,
        "start_date": start_date or "",
        "end_date": end_date or "",
        "gorev_filter": gorev_filter or "",
        "GOREVLER": UserProfile.GOREV_SECENEKLERI,
    }

    return render(request, "reports/staff_reports.html", context)


# 🧭 Yönetim Paneli
@login_required
def management_panel(request):
    user_groups = list(request.user.groups.values_list("name", flat=True))
    if not any(role in user_groups for role in ["patron", "mudur"]):
        return redirect("order_list")
    return render(request, "management_panel.html")
