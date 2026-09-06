import requests
print(requests.post('http://localhost:8000/api/events', headers={'Content-Type': 'application/x-www-form-urlencoded'}, data="title=test&description=testdesc&date=2026-05-15&time=12:00&venue=testvenue&category=Other").json())
