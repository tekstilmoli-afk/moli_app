from locust import HttpUser, task, between

class MoliLiveUser(HttpUser):
    wait_time = between(1, 3)  # Her istek arasında 1-3 saniye bekler

    @task(3)
    def list_orders(self):
        # Ana sayfa / sipariş listesi
        self.client.get("/")

    @task(1)
    def order_detail(self):
        # Örnek olarak order id=1 sayfasını açar (mevcut bir sipariş olmalı)
        self.client.get("/orders/1/")

    @task(1)
    def login_page(self):
        # Giriş sayfasını test eder
        self.client.get("/login/")

