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
            "renk",
            "beden",
            "adet",
            "teslim_tarihi",
            "aciklama",
            "resim",

            # 💰 Yeni eklenen alanlar
            "satis_fiyati",
            "para_birimi",
            "maliyet_uygulanan",
            "maliyet_para_birimi",
            "maliyet_override",
            "ekstra_maliyet",
        ]
        widgets = {
            "siparis_tarihi": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "teslim_tarihi": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "aciklama": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "urun_kodu": forms.TextInput(attrs={"class": "form-control"}),
            "renk": forms.TextInput(attrs={"class": "form-control"}),
            "beden": forms.TextInput(attrs={"class": "form-control"}),
            "adet": forms.NumberInput(attrs={"class": "form-control"}),
            "siparis_tipi": forms.Select(attrs={"class": "form-control"}),
            "musteri": forms.Select(attrs={"class": "form-control"}),

            # 💰 Eklenen alanların stilleri
            "satis_fiyati": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "para_birimi": forms.Select(attrs={"class": "form-control"}),
            "maliyet_uygulanan": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "maliyet_para_birimi": forms.Select(attrs={"class": "form-control"}),
            "maliyet_override": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "ekstra_maliyet": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # 🔎 Kullanıcı gruplarını küçük harfe çeviriyoruz
        user_groups = [g.name.lower() for g in user.groups.all()] if user else []

        # 🔒 Eğer kullanıcı patron veya müdür değilse bu alanları gizle
        if user and not any(g in ["patron", "mudur"] for g in user_groups):
            hidden_fields = [
                "satis_fiyati",
                "para_birimi",
                "maliyet_uygulanan",
                "maliyet_para_birimi",
                "maliyet_override",
                "ekstra_maliyet",
                "gitti_mi",
            ]
            for field in hidden_fields:
                if field in self.fields:
                    self.fields[field].widget = forms.HiddenInput()


# 👤 Müşteri Formu
class MusteriForm(forms.ModelForm):
    class Meta:
        model = Musteri
        fields = ["ad"]
        widgets = {
            "ad": forms.TextInput(attrs={"class": "form-control", "placeholder": "Müşteri adı giriniz"}),
        }
