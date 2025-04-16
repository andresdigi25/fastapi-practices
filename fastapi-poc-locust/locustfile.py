# locustfile.py
from locust import HttpUser, task, between

class ApiUser(HttpUser):
    wait_time = between(1, 3)

    @task(2)
    def create_item(self):
        self.client.post("/items/", json={"name": "test item", "description": "test description"})

    @task(3)
    def read_items(self):
        self.client.get("/items/")

    @task(1)
    def read_item(self):
        self.client.get("/items/1")