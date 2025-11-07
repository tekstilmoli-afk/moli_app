import requests
import os

def upload_to_supabase(file_obj):
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
    SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET_NAME', 'qr-codes')

    file_name = os.path.basename(file_obj.name)
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{file_name}"

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/octet-stream"
    }

    print("🛰️ Upload başlıyor →", upload_url)

    response = requests.post(upload_url, headers=headers, data=file_obj.read())

    print("🧾 Supabase yanıt:", response.status_code)
    print("🧾 Yanıt içeriği:", response.text[:500])  # ilk 500 karakter yeter

    if response.status_code in (200, 201):
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{file_name}"
        print("✅ Başarılı! Public URL:", public_url)
        return public_url
    else:
        print("❌ Supabase upload failed:", response.status_code)
        return None
