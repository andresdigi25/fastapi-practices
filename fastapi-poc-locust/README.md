docker-compose up --build

locust -f locustfile.py --host http://localhost:8000

locust -f locustfile.py --host http://localhost:8001