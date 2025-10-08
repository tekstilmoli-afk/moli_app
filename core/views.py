from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from openpyxl import Workbook

from .models import Order, Musteri
from .forms import OrderForm, MusteriForm


# 📋 Sipariş Listeleme (Cache + Select Related + Lazy filters)
@cache_page(60)  # 1 dakika boyunca listeyi cache’ler (yoğun sorgu yükünü azaltır)
def order_list(request):
    # İlişkili müşteri verisini tek sorguda almak için:
    orders = Order.objects.select_related("musteri").all()

    # 🔍 Genel arama
    q = request.GET.get("q", "").strip()
    if q:
        orders = orders.filter(
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

    # 🧰 Filtreler
    filters = {
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

    for field, value in filters.items():
        if value:
            orders = orders.filter(**{field: value})

    # ⬆️ Sıralama
    sort_col = request.GET.get("sort")
    sort_dir = request.GET.get("dir", "asc")
    if sort_col:
        orders = orders.order_by(f"-{sort_col}" if sort_dir == "desc" else sort_col)

    # 🔽 Dropdown filtre seçenekleri (değerler küçük listelerde tutulur)
    tip_options = Order.objects.values_list("siparis_tipi", flat=True).distinct()
    musteri_options = Order.objects.values_list("musteri__ad", flat=True).distinct()
    urun_options = Order.objects.values_list("urun_kodu", flat=True).distinct()
    renk_options = Order.objects.values_list("renk", flat=True).distinct()
    beden_options = Order.objects.values_list("beden", flat=True).distinct()
    adet_options = Order.objects.values_list("adet", flat=True).distinct()
    sip_tarih_options = Order.objects.values_list("siparis_tarihi", flat=True).distinct()
    tes_tarih_options = Order.objects.values_list("teslim_tarihi", flat=True).distinct()
    aciklama_options = Order.objects.values_list("aciklama", flat=True).distinct()

    context = {
        "orders": orders,
        "q": q,
        "current_sort": sort_col,
        "current_dir": sort_dir,
        "tip_options": tip_options,
        "musteri_options": musteri_options,
        "urun_options": urun_options,
        "renk_options": renk_options,
        "beden_options": beden_options,
        "adet_options": adet_options,
        "sip_tarih_options": sip_tarih_options,
        "tes_tarih_options": tes_tarih_options,
        "aciklama_options": aciklama_options,
        "tip_selected": filters["siparis_tipi__in"],
        "musteri_selected": filters["musteri__ad__in"],
        "urun_selected": filters["urun_kodu__in"],
        "renk_selected": filters["renk__in"],
        "beden_selected": filters["beden__in"],
        "adet_selected": filters["adet__in"],
        "sip_tarih_selected": filters["siparis_tarihi__in"],
        "tes_tarih_selected": filters["teslim_tarihi__in"],
        "aciklama_selected": filters["aciklama__in"],
    }
    return render(request, "core/order_list.html", context)


# ➕ Yeni Sipariş
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
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("musteri"), pk=pk)
    return render(request, "core/order_detail.html", {"order": order})


# 👤 Yeni Müşteri
def musteri_create(request):
    if request.method == "POST":
        form = MusteriForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("order_create")
    else:
        form = MusteriForm()
    return render(request, "core/musteri_form.html", {"form": form})


# 📊 Excel çıktı alma (filtrelerle uyumlu)
def export_orders_excel(request):
    orders = Order.objects.select_related("musteri").all()

    # Mevcut filtreleri yeniden uygula
    q = request.GET.get("q", "").strip()
    if q:
        orders = orders.filter(
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

    # Filtreleri tekrar uygula
    filters = {
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
    for field, value in filters.items():
        if value:
            orders = orders.filter(**{field: value})

    # 📘 Excel oluştur
    wb = Workbook()
    ws = wb.active
    ws.title = "Siparişler"

    headers = [
        "Sipariş No",
        "Sipariş Tipi",
        "Müşteri",
        "Ürün Kodu",
        "Renk",
        "Beden",
        "Adet",
        "Sipariş Tarihi",
        "Teslim Tarihi",
        "Açıklama",
    ]
    ws.append(headers)

    for order in orders:
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
    response["Content-Disposition"] = 'attachment; filename="siparisler.xlsx"'
    wb.save(response)
    return response
