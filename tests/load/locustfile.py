"""
Load testing with Locust.

Run with:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

Or headless:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
           --headless -u 50 -r 5 --run-time 60s
"""

from locust import HttpUser, between, task


class LibraryUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        """Register and login to get a JWT token."""
        import random

        self.username = f"loadtest_{random.randint(1, 999999)}"
        self.client.post(
            "/api/v1/users/register/",
            json={
                "username": self.username,
                "email": f"{self.username}@test.com",
                "password": "loadtest123!",
            },
        )
        response = self.client.post(
            "/api/v1/users/login/",
            json={
                "username": self.username,
                "password": "loadtest123!",
            },
        )
        if response.status_code == 200:
            token = response.json().get("access", "")
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(5)
    def list_books(self):
        self.client.get("/api/v1/books/")

    @task(3)
    def search_books(self):
        self.client.get("/api/v1/search/?q=python")

    @task(3)
    def autocomplete(self):
        for prefix in ["har", "dja", "the"]:
            self.client.get(f"/api/v1/search/autocomplete/?q={prefix}")

    @task(2)
    def get_book_detail(self):
        self.client.get("/api/v1/books/1/")

    @task(1)
    def get_top_books(self):
        self.client.get("/api/v1/analytics/top/")

    @task(1)
    def get_profile(self):
        self.client.get("/api/v1/users/me/")
