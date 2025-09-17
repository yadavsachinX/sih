# whatsapp_simulator.py
import requests, time, os
WEBHOOK = os.getenv("WEBHOOK", "http://127.0.0.1:8000/webhook/whatsapp")
test_msgs = [
    {"From":"+919900112233", "Body":"Water is unsaf on my location, smell odd"},
    {"From":"+919900112234", "Body":"Many kids have diarrhea in our hamlet"},
    {"From":"+919900112235", "Body":"Is it safe to drink rainwater without boiling?"}
]

for m in test_msgs:
    print("Send", m)
    res = requests.post(WEBHOOK, json=m, timeout=5)
    print(res.status_code, res.json())
    time.sleep(1)
