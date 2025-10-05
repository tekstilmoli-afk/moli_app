from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Sum
from django.http import HttpResponse
from openpyxl import Workbook

from .models import Order, Musteri
from .forms import OrderForm, MusteriForm


# 📋 Sipariş Listeleme
def order_list(request):
    orders = Order.objects.all()

    # 🔍 Genel arama
    q = request.GET.get("q", "")
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
    tip_filter = request.GET.getlist("siparis_tipi")
    musteri_filter = request.GET.getlist("musteri")
    urun_filter = request.GET.getlist("urun_kodu")
    renk_filter = request.GET.getlist("renk")
    beden_filter = request.GET.getlist("beden")
    adet_filter = request.GET.getlist("adet")
    sip_tarih_filter = request.GET.getlist("siparis_tarihi")
    tes_tarih_filter = request.GET.getlist("teslim_tarihi")
    aciklama_filter = request.GET.getlist("aciklama")

    if tip_filter:
        orders = orders.filter(siparis_tipi__in=tip_filter)
    if musteri_filter:
        orders = orders.filter(musteri__ad__in=musteri_filter)
    if urun_filter:
        orders = orders.filter(urun_kodu__in=urun_filter)
    if renk_filter:
        orders = orders.filter(renk__in=renk_filter)
    if beden_filter:
        orders = orders.filter(beden__in=beden_filter)
    if adet_filter:
        orders = orders.filter(adet__in=adet_filter)
    if sip_tarih_filter:
        orders = orders.filter(siparis_tarihi__in=sip_tarih_filter)
    if tes_tarih_filter:
        orders = orders.filter(teslim_tarihi__in=tes_tarih_filter)
    if aciklama_filter:
        orders = orders.filter(aciklama__in=aciklama_filter)

    # ⬆️ Sıralama
    sort_col = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "asc")
    if sort_col:
        if sort_dir == "desc":
            sort_col = f"-{sort_col}"
        orders = orders.order_by(sort_col)

    # 🔽 Dropdown filtre seçenekleri
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

        "tip_selected": tip_filter,
        "musteri_selected": musteri_filter,
        "urun_selected": urun_filter,
        "renk_selected": renk_filter,
        "beden_selected": beden_filter,
        "adet_selected": adet_filter,
        "sip_tarih_selected": sip_tarih_filter,
        "tes_tarih_selected": tes_tarih_filter,
        "aciklama_selected": aciklama_filter,
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
    order = get_object_or_404(Order, pk=pk)
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
    orders = Order.objects.all()

    # Filtre mantığı tekrar
    q = request.GET.get("q", "")
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

    tip_filter = request.GET.getlist("siparis_tipi")
    musteri_filter = request.GET.getlist("musteri")
    urun_filter = request.GET.getlist("urun_kodu")
    renk_filter = request.GET.getlist("renk")
    beden_filter = request.GET.getlist("beden")
    adet_filter = request.GET.getlist("adet")
    sip_tarih_filter = request.GET.getlist("siparis_tarihi")
    tes_tarih_filter = request.GET.getlist("teslim_tarihi")
    aciklama_filter = request.GET.getlist("aciklama")

    if tip_filter:
        orders = orders.filter(siparis_tipi__in=tip_filter)
    if musteri_filter:
        orders = orders.filter(musteri__ad__in=musteri_filter)
    if urun_filter:
        orders = orders.filter(urun_kodu__in=urun_filter)
    if renk_filter:
        orders = orders.filter(renk__in=renk_filter)
    if beden_filter:
        orders = orders.filter(beden__in=beden_filter)
    if adet_filter:
        orders = orders.filter(adet__in=adet_filter)
    if sip_tarih_filter:
        orders = orders.filter(siparis_tarihi__in=sip_tarih_filter)
    if tes_tarih_filter:
        orders = orders.filter(teslim_tarihi__in=tes_tarih_filter)
    if aciklama_filter:
        orders = orders.filter(aciklama__in=aciklama_filter)

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
