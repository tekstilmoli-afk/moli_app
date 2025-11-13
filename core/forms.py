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
            "siparis_tarihi": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "teslim_tarihi": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
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

        # 🧾 Müşteri listesini her seferinde dinamik olarak güncelle
        from .models import Musteri
        self.fields["musteri"].queryset = Musteri.objects.filter(aktif=True).order_by("ad")



        # 🧍 Kullanıcıyı form içinde sakla (save'te erişebilmek için)
        self.user = user

        # 🔎 Kullanıcı gruplarını belirle
        user_groups = [g.name.lower() for g in user.groups.all()] if user else []

        # 🔒 Eğer kullanıcı patron veya müdür değilse bazı alanları gizle
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

        print("🟡 [DEBUG] BEFORE SAVE → cleaned_data:", self.cleaned_data)

        user = getattr(self, 'user', None)
        if user and not user.groups.filter(name__in=["patron", "mudur"]).exists():
            # 👷‍♂️ Patron veya müdür değilse gizli alanları koru
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
            # 🔧 ManyToMany alanları da kaydet (musteri gibi)
            if hasattr(self, "save_m2m"):
                self.save_m2m()

        print("🟢 [DEBUG] AFTER SAVE →", instance.satis_fiyati, instance.maliyet_uygulanan)
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
