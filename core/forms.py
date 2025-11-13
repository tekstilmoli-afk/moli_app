from django import forms
from .models import Order, Musteri


# 🧾 SİPARİŞ FORMU
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "siparis_tipi",
            "musteri",
            "musteri_referans",
            "siparis_tarihi",
            "urun_kodu",
            "renk",
            "beden",
            "adet",
            "teslim_tarihi",
            "aciklama",
            "resim",
            # 💰 Fiyat & Maliyet alanları
            "satis_fiyati",
            "para_birimi",
            "maliyet_uygulanan",
            "maliyet_para_birimi",
            "maliyet_override",
            "ekstra_maliyet",
        ]
        widgets = {
            "siparis_tarihi": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d"
            ),
            "teslim_tarihi": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d"
            ),
            "aciklama": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "urun_kodu": forms.TextInput(attrs={"class": "form-control"}),
            "renk": forms.TextInput(attrs={"class": "form-control"}),
            "beden": forms.TextInput(attrs={"class": "form-control"}),
            "adet": forms.NumberInput(attrs={"class": "form-control"}),
            "siparis_tipi": forms.Select(attrs={"class": "form-control"}),
            "musteri": forms.Select(attrs={"class": "form-control"}),
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

        # 🧾 Yalnızca aktif müşterileri listede göster
        self.fields["musteri"].queryset = Musteri.objects.filter(aktif=True).order_by("ad")

        # 📌 Düzenleme modunda tarihlerin inputlarda görünmesi
        if self.instance and self.instance.pk:
            if self.instance.siparis_tarihi:
                self.fields["siparis_tarihi"].initial = self.instance.siparis_tarihi.strftime("%Y-%m-%d")
            if self.instance.teslim_tarihi:
                self.fields["teslim_tarihi"].initial = self.instance.teslim_tarihi.strftime("%Y-%m-%d")

        # 🧍 Kullanıcıyı sakla
        self.user = user

        # 🔎 Kullanıcı grupları
        user_groups = [g.name.lower() for g in user.groups.all()] if user else []

        # 🔒 Patron/müdür değilse maliyet & fiyat alanlarını gizle
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

    def save(self, commit=True):
        instance = super().save(commit=False)

        user = getattr(self, 'user', None)

        # Patron/müdür değilse gizli alanları dokunma — eski değerleri koru
        if user and not user.groups.filter(name__in=["patron", "mudur"]).exists():
            for field in [
                "satis_fiyati",
                "para_birimi",
                "maliyet_uygulanan",
                "maliyet_para_birimi",
                "maliyet_override",
                "ekstra_maliyet",
            ]:
                old_value = getattr(self.instance, field, None)
                setattr(instance, field, old_value)

        if commit:
            instance.save()
            if hasattr(self, "save_m2m"):
                self.save_m2m()

        return instance


# 👤 MÜŞTERİ FORMU
class MusteriForm(forms.ModelForm):
    class Meta:
        model = Musteri
        fields = ["ad"]
        widgets = {
            "ad": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Müşteri adı giriniz"
            }),
        }
