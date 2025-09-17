# main.py
import os
from fastapi import FastAPI, WebSocket, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select
from datetime import datetime
import asyncio

from db import init_db, get_session
from models import SensorReading, HealthReport, WhatsAppMessage, Fact, User
from services import notifier, llm_client
from ml.predictor import predict_outbreak

# init
app = FastAPI(title="Smart Health Surveillance - Full Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()
    # seed facts
    with next(get_session()) as s:
        cnt = s.exec(select(Fact)).all()
        if not cnt:
            facts = [
                "Boiling water for 1 minute kills most pathogens at sea level.",
                "Handwashing with soap reduces diarrheal disease by roughly 40%.",
                "Store drinking water in covered containers to prevent recontamination.",
                "Use chlorination tablets where available to disinfect water.",
                "Avoid open defecation near water sources to reduce contamination.",
                "Clear-looking water can still be contaminated by microbes.",
                "Turbid water increases likelihood of pathogens attaching to particles."
            ]
            for f in facts:
                s.add(Fact(text=f))
            s.commit()

# --------- Helpers ----------
def validate_api_key(x_api_key: str | None = None):
    # simple placeholder for device auth; in real-prod use JWT / DB-stored keys
    API_KEY = os.getenv("BACKEND_API_KEY", "devkey")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

# --------- Root ----------
@app.get("/")
def root():
    return {"status": "ok", "message": "Smart Health Surveillance backend is up."}

# --------- Sensor ingestion ----------
@app.post("/report/sensor")
async def ingest_sensor(payload: dict, x_api_key: str | None = None):
    # device must supply X-API-KEY header (simple auth)
    try:
        validate_api_key(x_api_key)
    except HTTPException:
        raise

    # parse payload robustly
    device_id = payload.get("device_id", "unknown")
    ts = payload.get("timestamp")
    try:
        ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.utcnow()
    except:
        ts_dt = datetime.utcnow()
    tds = float(payload.get("tds", 0.0))
    turb = float(payload.get("turbidity", 0.0))
    ph = payload.get("ph", None)
    bflag = payload.get("bacteria_flag", None)

    reading = SensorReading(device_id=device_id, timestamp=ts_dt, tds=tds, turbidity=turb, ph=ph, bacteria_flag=bflag)
    with next(get_session()) as s:
        s.add(reading)
        s.commit()

    # real-time risk using XGBoost predictor: fetch recent case counts heuristically
    # for demo we'll pass dummy rainfall and cases; later replace with real features
    rainfall = payload.get("rainfall", 20.0)
    recent_cases = int(payload.get("reported_cases", 0))
    pred = predict_outbreak(tds, turb, ph or 7.0, rainfall, recent_cases)
    # threshold rules and broadcast
    level = pred["risk_label"]
    if level in ("HIGH", "MEDIUM"):
        alert = {
            "type": "sensor_alert",
            "device_id": device_id,
            "timestamp": ts_dt.isoformat(),
            "tds": tds,
            "turbidity": turb,
            "risk": pred
        }
        asyncio.create_task(notifier.broadcast(alert))

    return {"status": "ok", "prediction": pred}

# --------- Health report ----------
@app.post("/report/health")
async def report_health(payload: dict):
    with next(get_session()) as s:
        hr = HealthReport(
            user_phone=payload.get("user_phone"),
            location=payload.get("location"),
            symptoms=",".join(payload.get("symptoms", [])) if isinstance(payload.get("symptoms", []), list) else payload.get("symptoms"),
            water_source=payload.get("water_source"),
            source=payload.get("source", "app")
        )
        s.add(hr)
        s.commit()
    # optionally run ML using latest sensor data
    # (for demo use last sensor reading)
    with next(get_session()) as s:
        last = s.exec(select(SensorReading).order_by(SensorReading.timestamp.desc()).limit(1)).first()
    tds = last.tds if last else 100.0
    turb = last.turbidity if last else 1.0
    pred = predict_outbreak(tds, turb, 7.0, 10.0, len((payload.get("symptoms") or [])))
    if pred["risk_label"] == "HIGH":
        asyncio.create_task(notifier.broadcast({"type": "outbreak_pred", "pred": pred}))
    return {"status": "ok", "prediction": pred}

# --------- WhatsApp webhook ----------
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    body = await request.json() if request.headers.get("content-type","").startswith("application/json") else await request.form()
    # Twilio provides 'From' and 'Body' in form
    sender = body.get("From") or body.get("sender") or body.get("from") or "unknown"
    message = body.get("Body") or body.get("body") or body.get("message") or ""
    # persist
    with next(get_session()) as s:
        w = WhatsAppMessage(sender=sender, message=message)
        s.add(w)
        s.commit()
    # simple classification using llm_client
    parsed = llm_client.llm_fact_check(message)
    # If LLM returns parsed issue, create HealthReport (demo)
    # respond (in production you'd call Twilio API to reply)
    if "unsafe water" in message.lower() or parsed.get("verdict","").startswith("likely_false") == False:
        # broadcast short alert
        await notifier.broadcast({"type":"whatsapp", "sender":sender, "message":message})
    return JSONResponse({"status":"received", "analysis": parsed})

# --------- Facts ----------
@app.get("/facts")
def get_fact(n: int = 1, lang: str = "en"):
    with next(get_session()) as s:
        q = s.exec(select(Fact).where(Fact.language == lang)).all()
        if not q:
            return {"facts": []}
        # rotate / sample
        import random
        pick = random.sample(q, min(n, len(q)))
        return {"facts": [f.text for f in pick]}

# --------- WebSocket alerts ----------
@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await notifier.register(ws)
    try:
        while True:
            # keep alive and optionally receive pings
            msg = await ws.receive_text()
            # echo or use as filter
            await ws.send_text("pong")
    except Exception:
        await notifier.unregister(ws)

# --------- Video signaling (very simple) ----------
rooms = {}
@app.post("/video/room/{room_id}/signal")
def video_signal(room_id: str, payload: dict):
    rooms.setdefault(room_id, {"offers": [], "answers": [], "candidates": []})
    typ = payload.get("type")
    rooms[room_id].setdefault(typ + "s", []).append(payload)
    return {"status":"ok", "room_state": rooms[room_id]}

@app.get("/video/room/{room_id}")
def video_room(room_id: str):
    return rooms.get(room_id, {})

# --------- Admin endpoints ----------
@app.get("/admin/sensors/recent")
def recent_sensors(limit: int = 30):
    with next(get_session()) as s:
        rows = s.exec(select(SensorReading).order_by(SensorReading.timestamp.desc()).limit(limit)).all()
        return {"count": len(rows), "rows": [r.__dict__ for r in rows]}

@app.get("/admin/whatsapp/recent")
def recent_whatsapp(limit: int = 20):
    with next(get_session()) as s:
        rows = s.exec(select(WhatsAppMessage).order_by(WhatsAppMessage.received_at.desc()).limit(limit)).all()
        return {"count": len(rows), "rows": [r.__dict__ for r in rows]}

# --------- Run ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
