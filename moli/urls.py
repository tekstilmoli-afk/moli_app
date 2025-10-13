from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views  # 👈 eğer view'lar core uygulamasında ise

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.order_list, name="order_list"),
    path("order/new/", views.order_create, name="order_create"),
    path("order/<int:pk>/", views.order_detail, name="order_detail"),
    path("musteri/new/", views.musteri_create, name="musteri_create"),
    path("export/excel/", views.export_orders_excel, name="export_orders_excel"),
]

# ✅ QR kodları ve medya dosyalarını servis et
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)