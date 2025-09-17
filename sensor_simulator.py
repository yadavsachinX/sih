# sensor_simulator.py
import requests, random, time, datetime, os
SERVER = os.getenv("SERVER", "http://127.0.0.1:8000/report/sensor")
API_KEY = os.getenv("BACKEND_API_KEY", "devkey")

def gen_reading():
    if random.random() < 0.12:
        tds = random.uniform(700, 1200)
        turb = random.uniform(10, 80)
    elif random.random() < 0.25:
        tds = random.uniform(400, 700)
        turb = random.uniform(4, 12)
    else:
        tds = random.uniform(20, 350)
        turb = random.uniform(0.1, 4.5)
    payload = {
        "device_id": "sim_sim_01",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "tds": round(tds,2),
        "turbidity": round(turb,2),
        "ph": round(random.uniform(6.5, 8.2),2),
        "rainfall": round(random.uniform(0, 200),1),
        "reported_cases": random.randint(0, 12)
    }
    return payload

if __name__ == "__main__":
    print("Sim started ->", SERVER)
    while True:
        p = gen_reading()
        try:
            r = requests.post(SERVER, json=p, headers={"X-API-KEY": API_KEY}, timeout=6)
            print("POST", p, "->", r.status_code, r.json())
        except Exception as e:
            print("Err:", e)
        time.sleep(3)
