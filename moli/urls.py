from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import logout
from django.shortcuts import redirect
from core import views  # 👈 sadece core.views yeterli

# 👇 GET isteğini de destekleyen logout fonksiyonu
def logout_view(request):
    logout(request)
    return redirect('/login/')

urlpatterns = [
    # 🧭 Admin paneli
    path("admin/", admin.site.urls),

    # 🔐 Login / Logout işlemleri
    path("login/", views.custom_login, name="login"),
    path("custom-login/", views.custom_login, name="custom_login"),
    path("logout/", logout_view, name="logout"),

    # 🏠 Ana sayfa (Sipariş Listesi)
    path("", views.order_list, name="order_list"),

    # 🧭 Yönetim Paneli (Sadece patron & müdür)
    path("management/", views.management_panel, name="management_panel"),

    # 📝 Sipariş işlemleri
    path("order/new/", views.order_create, name="order_create"),
    path("order/<int:pk>/", views.order_detail, name="order_detail"),
    path("order/<int:pk>/edit/", views.order_edit, name="order_edit"),
    path("orders/<int:pk>/update/", views.update_stage, name="update_stage"),
    path("orders/<int:pk>/delete/", views.order_delete, name="order_delete"),
    path("orders/<int:pk>/upload-image/", views.order_upload_image, name="order_upload_image"),
    path("orders/<int:pk>/add-image/", views.order_add_image, name="order_add_image"),
    path("images/<int:image_id>/delete/", views.delete_order_image, name="delete_order_image"),
    path("images/<int:image_id>/", views.view_image, name="view_image"),

    # 👤 Müşteri işlemleri
    path("musteri/new/", views.musteri_create, name="musteri_create"),

    # AJAX müşteri ekleme
    path("ajax/musteri/ekle/", views.ajax_musteri_ekle, name="ajax_musteri_ekle"),



    # 👥 Kullanıcı Yönetimi
    path("users/", views.user_management_view, name="user_management"),

    # 📊 Raporlama Sayfaları
    path("reports/", views.reports_view, name="reports"),
    path("staff-reports/", views.staff_reports_view, name="staff_reports"),
    path("reports/fast/", views.fast_profit_report, name="fast_profit_report"),
    path("reports/giden-urunler/", views.giden_urunler_raporu, name="giden_urunler_raporu"),
    path("reports/home/", views.reports_home, name="reports_home"),

    # 🧵 Fasoncu ve Nakışçı Raporları
    path("reports/fasoncu/", views.fasoncu_raporu, name="fasoncu_raporu"),
    path("reports/nakisci/", views.nakisci_raporu, name="nakisci_raporu"),

    # 💰 Ürün Maliyet Yönetimi
    path("product-costs/", views.product_cost_list, name="product_cost_list"),

    # 🧵 Üretim geçmişi silme
    path("events/<int:event_id>/delete/", views.delete_order_event, name="delete_order_event"),

    # 🤖 Asistan
    path("asistan/", views.ai_assistant_view, name="ai_assistant"),
    path("api/assistant/", views.ai_assistant_api, name="ai_assistant_api"),
    
    

    # 🧶 Fasoncu / Nakışçı
    path("fasoncu/yeni/", views.fasoncu_yeni, name="fasoncu_yeni"),
    path("nakisci/yeni/", views.nakisci_ekle, name="nakisci_ekle"),

    # 📦 Stok & Depo
    path("order/<int:order_id>/stok-ekle/", views.stok_ekle, name="stok_ekle"),
    path("depolar/", views.depo_ozet, name="depo_ozet"),
    path("depolar/detay/<str:depo_adi>/", views.depo_detay, name="depo_detay"),
    path("depolar/arama/", views.depo_arama, name="depo_arama"),
    path("depolar/hazirdan-ver/<int:stok_id>/", views.hazirdan_ver, name="hazirdan_ver"),

    path("orders/<int:pk>/cikti-alindi/", views.cikti_alindi, name="cikti_alindi"),
]

# 📁 Statik & Medya (sadece DEBUG modda)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
