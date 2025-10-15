from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required  # 👈 EKLENDİ
from openpyxl import Workbook

from .models import Order, Musteri
from .forms import OrderForm, MusteriForm


# 🧠 Ortak filtreleme fonksiyonu (hem liste hem Excel export için kullanılıyor)
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


# 📋 Sipariş Listeleme (Artık cache yok, login zorunlu)
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

    current_sort = request.GET.get("sort")
    current_dir = request.GET.get("dir", "asc")

    paginator = Paginator(qs, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "orders": page_obj,
        "q": request.GET.get("q", "").strip(),
        "current_sort": current_sort,
        "current_dir": current_dir,
        "tip_options": Order.objects.values_list("siparis_tipi", flat=True).distinct(),
        "musteri_options": Order.objects.values_list("musteri__ad", flat=True).distinct(),
        "urun_options": Order.objects.values_list("urun_kodu", flat=True).distinct(),
        "renk_options": Order.objects.values_list("renk", flat=True).distinct(),
        "beden_options": Order.objects.values_list("beden", flat=True).distinct(),
        "adet_options": Order.objects.values_list("adet", flat=True).distinct(),
        "sip_tarih_options": Order.objects.values_list("siparis_tarihi", flat=True).distinct(),
        "tes_tarih_options": Order.objects.values_list("teslim_tarihi", flat=True).distinct(),
        "aciklama_options": Order.objects.values_list("aciklama", flat=True).distinct(),
        "tip_selected": request.GET.getlist("siparis_tipi"),
        "musteri_selected": request.GET.getlist("musteri"),
        "urun_selected": request.GET.getlist("urun_kodu"),
        "renk_selected": request.GET.getlist("renk"),
        "beden_selected": request.GET.getlist("beden"),
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string("core/order_table_partial.html", context, request=request)
        return JsonResponse({"html": html})

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


# 📌 Sipariş Detay
@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("musteri").only(
            "id", "siparis_numarasi", "siparis_tipi", "urun_kodu", "renk", "beden",
            "adet", "siparis_tarihi", "teslim_tarihi", "aciklama",
            "musteri__ad", "qr_code_url", "resim",
            "kesim_yapan", "kesim_tarihi",
            "dikim_yapan", "dikim_tarihi",
            "susleme_yapan", "susleme_tarihi",
            "hazir_yapan", "hazir_tarihi",
            "sevkiyat_yapan", "sevkiyat_tarihi",
        ),
        pk=pk
    )
    return render(request, "core/order_detail.html", {"order": order})


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


# 📊 Excel çıktı alma
@login_required
def export_orders_excel(request):
    qs = apply_filters(request, Order.objects.select_related("musteri"))

    wb = Workbook()
    ws = wb.active
    ws.title = "Siparişler"

    headers = [
        "Sipariş No", "Sipariş Tipi", "Müşteri", "Ürün Kodu", "Renk",
        "Beden", "Adet", "Sipariş Tarihi", "Teslim Tarihi", "Açıklama"
    ]
    ws.append(headers)

    for order in qs:
        ws.append([
            order.siparis_numarasi,
            order.siparis_tipi,
            order.musteri.ad if order.musteri else "",
            order.urun_kodu,
            order.renk or "",
            order.beden or "",
            order.adet,
            order.siparis_tarihi.strftime("%d.%m.%Y") if order.siparis_tarihi else "",
            order.teslim_tarihi.strftime("%d.%m.%Y") if order.teslim_tarihi else "",
            order.aciklama or "",
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename=\"siparisler.xlsx\"'
    wb.save(response)
    return response


# 🧠 Müşteri arama
@login_required
def musteri_search(request):
    q = request.GET.get("q", "").strip()
    results = []
    if q:
        matches = Musteri.objects.filter(ad__icontains=q).order_by("ad")[:20]
    else:
        matches = Musteri.objects.all().order_by("ad")[:20]

    for m in matches:
        results.append({
            "id": m.ad,
            "text": m.ad
        })

    return JsonResponse(results, safe=False)
