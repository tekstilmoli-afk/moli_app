from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views
from django.contrib.auth import logout
from django.shortcuts import redirect


# 👇 GET isteğini de destekleyen logout fonksiyonu
def logout_view(request):
    logout(request)
    return redirect('/login/')


urlpatterns = [
    # 🧭 Admin paneli
    path("admin/", admin.site.urls),

    # 🔐 Özel giriş ekranı
    path("custom-login/", views.custom_login, name="custom_login"),

    # 🏠 Ana sayfa (Sipariş Listesi)
    path("", views.order_list, name="order_list"),

    # 🧭 Yönetim Paneli (Sadece patron & müdür)
    path("management/", views.management_panel, name="management_panel"),

    # 📝 Sipariş işlemleri
    path("order/new/", views.order_create, name="order_create"),
    path("order/<int:pk>/", views.order_detail, name="order_detail"),
    path("order/<int:pk>/edit/", views.order_edit, name="order_edit"),  # ✅ Düzenleme sayfası

    # 🧱 Üretim aşamalarını güncelleme
    path("orders/<int:pk>/update/", views.update_stage, name="update_stage"),
    path("orders/<int:pk>/delete/", views.order_delete, name="order_delete"),
    path("orders/<int:pk>/upload-image/", views.order_upload_image, name="order_upload_image"),

    # ✅ Çoklu görsel yükleme
    path("orders/<int:pk>/add-image/", views.order_add_image, name="order_add_image"),

    # ✅ Görsel silme (YENİ)
    path("images/<int:image_id>/delete/", views.delete_order_image, name="delete_order_image"),

    # ✅ Görseli ayrı sayfada görüntüleme
    path("images/<int:image_id>/", views.view_image, name="view_image"),

    # 👤 Müşteri işlemleri
    path("musteri/new/", views.musteri_create, name="musteri_create"),

    # 🔐 Login / Logout işlemleri
    path("login/", views.custom_login, name="login"),
    path("logout/", logout_view, name="logout"),

    # 👥 Kullanıcı Yönetimi
    path("users/", views.user_management_view, name="user_management"),

    # 📊 Raporlama Sayfaları
    path("reports/", views.reports_view, name="reports"),
    path("staff-reports/", views.staff_reports_view, name="staff_reports"),
    path("reports/fast/", views.fast_profit_report, name="fast_profit_report"),
    path("reports/giden-urunler/", views.giden_urunler_raporu, name="giden_urunler_raporu"),
    path("reports/home/", views.reports_home, name="reports_home"),

    # 💰 Ürün Maliyet Yönetimi
    path("product-costs/", views.product_cost_list, name="product_cost_list"),

    # 🧵 Üretim geçmişi silme (YENİ)
    path("events/<int:event_id>/delete/", views.delete_order_event, name="delete_order_event"),
]


# 📌 Statik dosyalar (CSS, JS)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# 📌 Medya dosyaları (QR kodları, yüklenen resimler)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
