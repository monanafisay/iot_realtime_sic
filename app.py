import streamlit as st
import pandas as pd
import json
import time
import queue
import threading
from datetime import datetime, timezone, timedelta
import plotly.graph_objs as go
import paho.mqtt.client as mqtt

# ---------------------------
# CONFIG
# ---------------------------
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT   = 1883

TOPIC_ASAP   = "alat/asap"
TOPIC_CAHAYA = "alat/cahaya"
TOPIC_SUHU   = "alat/suhu"
TOPIC_BUZZER = "alat/buzzer/sic"

TZ = timezone(timedelta(hours=7))
def now_str():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

GLOBAL_Q = queue.Queue()

# ---------------------------
# STREAMLIT PAGE
# ---------------------------
st.set_page_config(page_title="IoT ESP32 Dashboard", layout="wide")
st.title("Realtime Dashboard ESP32 — MQ2, LDR, DHT22")

# ---------------------------
# SESSION STATE
# ---------------------------
for key in ["logs_asap", "logs_cahaya", "logs_suhu",
            "latest_asap", "latest_cahaya", "latest_suhu",
            "mqtt_started"]:
    if key not in st.session_state:
        st.session_state[key] = [] if "logs" in key else None

# ---------------------------
# MQTT CALLBACKS
# ---------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        GLOBAL_Q.put({"type": "status", "ok": True})
        client.subscribe(TOPIC_ASAP)
        client.subscribe(TOPIC_CAHAYA)
        client.subscribe(TOPIC_SUHU)
    else:
        GLOBAL_Q.put({"type": "status", "ok": False})

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    try:
        data = json.loads(payload)
    except:
        return

    GLOBAL_Q.put({
        "type": msg.topic,
        "data": data,
        "ts": now_str()
    })

# ---------------------------
# START MQTT THREAD (FIXED)
# ---------------------------
def start_mqtt():
    def worker():
        c = mqtt.Client()
        c.on_connect = on_connect
        c.on_message = on_message
        while True:
            try:
                c.connect(MQTT_BROKER, MQTT_PORT, 60)
                c.loop_forever()
            except Exception as e:
                GLOBAL_Q.put({"type": "err", "msg": str(e)})
                time.sleep(3)

    if not st.session_state.mqtt_started:
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        # prevent Streamlit rerun from killing the thread (Cloud FIX)
        try:
            import streamlit.runtime.scriptrunner as scriptrunner
            scriptrunner.add_script_run_ctx(thread)
        except:
            pass

        st.session_state.mqtt_started = True

start_mqtt()

# ---------------------------
# PROCESS QUEUE
# ---------------------------
def process_queue():
    while not GLOBAL_Q.empty():
        item = GLOBAL_Q.get()
        tp = item["type"]

        if tp == TOPIC_ASAP:
            st.session_state.latest_asap = item
            st.session_state.logs_asap.append(item)

        elif tp == TOPIC_CAHAYA:
            st.session_state.latest_cahaya = item
            st.session_state.logs_cahaya.append(item)

        elif tp == TOPIC_SUHU:
            st.session_state.latest_suhu = item
            st.session_state.logs_suhu.append(item)

process_queue()

# ---------------------------
# AUTO REFRESH
# ---------------------------
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=2000, key="refresh")
except:
    pass

# ---------------------------
# UI LAYOUT
# ---------------------------
left, right = st.columns([1, 2])

with left:
    st.header("MQTT Status")
    st.success("Connected to HiveMQ")    

    st.header("Kondisi Terakhir")

    if st.session_state.latest_asap:
        d = st.session_state.latest_asap["data"]
        st.write(f"**Asap:** {d['nilai']} ({d['status']})")

    if st.session_state.latest_cahaya:
        d = st.session_state.latest_cahaya["data"]
        st.write(f"**Cahaya:** {d['nilai']} ({d['status']})")

    if st.session_state.latest_suhu:
        d = st.session_state.latest_suhu["data"]
        st.write(f"**Suhu:** {d['nilai']}°C ({d['status']})")

    st.markdown("---")
    st.header("Kontrol Buzzer")

    col1, col2 = st.columns(2)
    if col1.button("BUZZER ON"):
        c = mqtt.Client()
        c.connect(MQTT_BROKER, MQTT_PORT)
        c.publish(TOPIC_BUZZER, "ON")
        c.disconnect()
        st.success("Buzzer ON dikirim")

    if col2.button("BUZZER OFF"):
        c = mqtt.Client()
        c.connect(MQTT_BROKER, MQTT_PORT)
        c.publish(TOPIC_BUZZER, "OFF")
        c.disconnect()
        st.success("Buzzer OFF dikirim")

with right:
    st.header("Grafik Sensor")

    # ---- ASAP ----
    dfA = pd.DataFrame([{
        "ts": r["ts"],
        "nilai": r["data"]["nilai"]
    } for r in st.session_state.logs_asap][-200:])

    if not dfA.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dfA["ts"], y=dfA["nilai"], mode="lines+markers", name="Asap"))
        fig.update_layout(height=250)
        st.subheader("Asap (MQ2)")
        st.plotly_chart(fig, use_container_width=True)

    # ---- CAHAYA ----
    dfC = pd.DataFrame([{
        "ts": r["ts"],
        "nilai": r["data"]["nilai"]
    } for r in st.session_state.logs_cahaya][-200:])

    if not dfC.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dfC["ts"], y=dfC["nilai"], mode="lines+markers", name="Cahaya"))
        fig.update_layout(height=250)
        st.subheader("Cahaya (LDR)")
        st.plotly_chart(fig, use_container_width=True)

    # ---- SUHU ----
    dfS = pd.DataFrame([{
        "ts": r["ts"],
        "nilai": r["data"]["nilai"]
    } for r in st.session_state.logs_suhu][-200:])

    if not dfS.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dfS["ts"], y=dfS["nilai"], mode="lines+markers", name="Suhu"))
        fig.update_layout(height=250)
        st.subheader("Suhu (DHT22)")
        st.plotly_chart(fig, use_container_width=True)
