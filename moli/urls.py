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

    # 🏠 Ana sayfa (Sipariş Listesi)
    path("", views.order_list, name="order_list"),

    # 🧭 Yönetim Paneli (Sadece patron & müdür)
    path("management/", views.management_panel, name="management_panel"),

    # 📝 Sipariş işlemleri
    path("order/new/", views.order_create, name="order_create"),
    path("order/<int:pk>/", views.order_detail, name="order_detail"),

    # 🧱 Üretim aşamalarını güncelleme (butonlar için)
    path("orders/<int:pk>/update/", views.update_stage, name="update_stage"),  # 👈 mevcut
    path("orders/<int:pk>/delete/", views.order_delete, name="order_delete"),  # 🗑️ SİLME URL'İ

    # 👤 Müşteri işlemleri
    path("musteri/new/", views.musteri_create, name="musteri_create"),

    # 🔐 Login / Logout işlemleri
    path("login/", views.custom_login, name="login"),  # ✅ Özel login sayfası
    path("logout/", logout_view, name="logout"),       # ✅ GET logout

    # 👥 Kullanıcı Yönetimi
    path("users/", views.user_management_view, name="user_management"),

    # 📊 Raporlama Sayfaları
    path("reports/", views.reports_view, name="reports"),              # ✅ Genel Üretim Raporu
    path("staff-reports/", views.staff_reports_view, name="staff_reports"),  # ✅ Personel Raporu
]

# 📌 Statik dosyalar (CSS, JS) için ayar
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# 📌 Medya dosyaları (QR kodları, yüklenen resimler)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
