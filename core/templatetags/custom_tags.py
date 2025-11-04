from django import template

register = template.Library()

TRANSLATIONS = {
    # 🔹 Kesim
    "kesim_durum basladi": "Kesime Başlandı",
    "kesim_durum kismi_bitti": "Kısmi Kesim Yapıldı",
    "kesim_durum bitti": "Kesildi",

    # 🔹 Dikim
    "dikim_durum basladi": "Dikime Başlandı",
    "dikim_durum kismi_bitti": "Kısmi Dikim Yapıldı",
    "dikim_durum bitti": "Dikildi",

    # 🔹 Süsleme
    "susleme_durum basladi": "Süslemeye Başlandı",
    "susleme_durum kismi_bitti": "Kısmi Süsleme Yapıldı",
    "susleme_durum bitti": "Süsleme Tamamlandı",

    # 🔹 Nakış / Fason
    "nakis_durumu verildi": "Nakışa Verildi",
    "nakis_durumu alindi": "Nakış Alındı",
    "dikim_fason_durumu verildi": "Fason Dikim Verildi",
    "dikim_fason_durumu alindi": "Fason Dikim Alındı",
    "susleme_fason_durumu verildi": "Fason Süsleme Verildi",
    "susleme_fason_durumu alindi": "Fason Süsleme Alındı",

    # 🔹 Sevkiyat
    "sevkiyat_durum gonderildi": "Sevkiyata Gönderildi",

    # 🔹 Sıraya Alınanlar
    "dikim_durum sıraya_alındı": "Dikime Alındı",
    "susleme_durum sıraya_alındı": "Süsleme Sırasına Alındı",
}

@register.filter
def get_item(dictionary, key):
    """Sözlüklerden key ile veri çekmek için yardımcı filtre."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def stage_translate(value):
    """Üretim aşaması kodlarını anlamlı Türkçe kelimelere çevirir."""
    if not value:
        return "-"
    return TRANSLATIONS.get(value.strip(), value)
