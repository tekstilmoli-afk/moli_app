from django import forms
from .models import Order, Musteri


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "siparis_tipi",
            "musteri",
            "siparis_tarihi",
            "urun_kodu",
            "renk",           # 🆕 eklendi
            "beden",          # 🆕 eklendi
            "adet",
            "teslim_tarihi",
            "aciklama",
            "resim",
        ]
        widgets = {
            "siparis_tarihi": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "teslim_tarihi": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "aciklama": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "urun_kodu": forms.TextInput(attrs={"class": "form-control"}),
            "renk": forms.TextInput(attrs={"class": "form-control"}),   # 🆕 eklendi
            "beden": forms.TextInput(attrs={"class": "form-control"}),  # 🆕 eklendi
            "adet": forms.NumberInput(attrs={"class": "form-control"}),
            "siparis_tipi": forms.Select(attrs={"class": "form-control"}),
            "musteri": forms.Select(attrs={"class": "form-control"}),
        }


class MusteriForm(forms.ModelForm):
    class Meta:
        model = Musteri
        fields = ["ad"]
        widgets = {
            "ad": forms.TextInput(attrs={"class": "form-control", "placeholder": "Müşteri adı giriniz"}),
        }
