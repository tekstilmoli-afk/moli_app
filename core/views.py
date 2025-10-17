from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Max
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from openpyxl import Workbook

from .models import Order, Musteri, Nakisci, Fasoncu, OrderEvent
from .forms import OrderForm, MusteriForm


# 🧠 Ortak filtreleme fonksiyonu
def apply_filters(request, qs):
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(siparis_numarasi__icontains=q) |
            Q(siparis_tipi__icontains=q) |
            Q(musteri__ad__icontains=q) |
            Q(urun_kodu__icontains=q) |
            Q(renk__icontains=q) |
            Q(beden__icontains=q) |
            Q(adet__icontains=q) |
            Q(siparis_tarihi__icontains=q) |
            Q(teslim_tarihi__icontains=q) |
            Q(aciklama__icontains=q)
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
            "id", "siparis_numarasi", "siparis_tipi", "urun_kodu", "renk", "beden",
            "adet", "siparis_tarihi", "teslim_tarihi", "aciklama",
            "musteri__ad", "qr_code_url", "resim",
            "kesim_yapan", "kesim_tarihi",
            "dikim_yapan", "dikim_tarihi",
            "susleme_yapan", "susleme_tarihi",
            "hazir_yapan", "hazir_tarihi",
            "sevkiyat_yapan", "sevkiyat_tarihi",
        )
    )

    qs = apply_filters(request, qs)

    if not qs.query.order_by:
        qs = qs.order_by('-id')

    paginator = Paginator(qs, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # 📌 Her sipariş için en son OrderEvent kaydını çek
    last_events = {
        e['order']: e for e in (
            OrderEvent.objects
            .values('order')
            .annotate(last_time=Max('timestamp'))
        )
    }

    # En son event'in detayını da çek
    for order in page_obj:
        latest_event = (
            OrderEvent.objects
            .filter(order=order)
            .order_by('-timestamp')
            .first()
        )
        order.last_event = latest_event  # 👈 Template'te kullanacağız

    context = {"orders": page_obj}
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
    fasoncular = Fasoncu.objects.all()
    events = OrderEvent.objects.filter(order=order).order_by("timestamp")

    if request.user.is_staff:
        allowed = {
            'kesim_durum','dikim_durum','susleme_durum','hazir_durum','sevkiyat_durum',
            'dikim_fason','dikim_fasoncu','dikim_fason_durumu',
            'susleme_fason','susleme_fasoncu','susleme_fason_durumu',
            'nakis_durumu','nakisci',
        }
    else:
        allowed = {
            'dikim_durum','nakis_durumu','nakisci',
            'susleme_durum','dikim_fason','dikim_fasoncu','dikim_fason_durumu',
            'susleme_fason','susleme_fasoncu','susleme_fason_durumu',
        }

    return render(request, "core/order_detail.html", {
        "order": order,
        "nakisciler": nakisciler,
        "fasoncular": fasoncular,
        "allowed": allowed,
        "is_admin": request.user.is_staff,
        "events": events
    })


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
            return redirect("/")
        else:
            return render(request, "registration/custom_login.html", {"error": True})

    return render(request, "registration/custom_login.html")


# ✍️ Üretim aşamalarını güncelleyen view + geçmiş kaydı
@login_required
def update_stage(request, pk):
    order = get_object_or_404(Order, pk=pk)
    stage = request.GET.get('stage') or request.POST.get('stage')
    value = request.GET.get('value') or request.POST.get('value')

    if not stage or not value:
        return HttpResponseForbidden('Eksik veri')

    print("🟡 STAGE DEĞERİ:", stage)
    print("🟡 VALUE DEĞERİ:", value)

    username = request.user.username
    now = timezone.now()

    # Geçmiş kaydı ekle
    OrderEvent.objects.create(
        order=order,
        user=username,
        stage=stage,
        value=value,
        timestamp=now
    )

    order.refresh_from_db()
    events = OrderEvent.objects.filter(order=order).order_by("timestamp")
    html = render_to_string("core/_uretim_paneli.html", {"order": order, "events": events})
    return HttpResponse(html)
