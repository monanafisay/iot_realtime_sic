import streamlit as st
import paho.mqtt.client as mqtt
import json
import joblib
from streamlit_autorefresh import st_autorefresh

# -------------------------------------------
# LOAD MODEL
# -------------------------------------------
model = joblib.load("model_iot_sic.pkl")

# -------------------------------------------
# GLOBAL SENSOR STORAGE
# -------------------------------------------
latest_data = {
    "suhu": None,
    "asap": None,
    "cahaya": None
}

# -------------------------------------------
# MQTT CALLBACKS
# -------------------------------------------
def on_connect(client, userdata, flags, rc):
    client.subscribe("alat/suhu")
    client.subscribe("alat/asap")
    client.subscribe("alat/cahaya")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()

    try:
        data = json.loads(payload)
        nilai = data["nilai"]
    except:
        print("JSON tidak valid:", payload)
        return

    if topic == "alat/suhu":
        latest_data["suhu"] = nilai
    elif topic == "alat/asap":
        latest_data["asap"] = nilai
    elif topic == "alat/cahaya":
        latest_data["cahaya"] = nilai

# -------------------------------------------
# MQTT CLIENT SETUP
# -------------------------------------------
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("broker.hivemq.com", 1883, 60)
client.loop_start()

# -------------------------------------------
# STREAMLIT DASHBOARD
# -------------------------------------------
st.set_page_config(page_title="IoT Smart Monitoring", layout="centered")
st.title("IoT Smart Monitoring – Realtime AI Dashboard")

# refresh halaman setiap 1000 ms (1 detik)
st_autorefresh(interval=1000, key="refresher")

st.subheader("Sensor Data Realtime")

suhu = latest_data["suhu"]
asap = latest_data["asap"]
cahaya = latest_data["cahaya"]

col1, col2, col3 = st.columns(3)
col1.metric("Suhu (°C)", suhu if suhu is not None else "-")
col2.metric("Asap", asap if asap is not None else "-")
col3.metric("Cahaya", cahaya if cahaya is not None else "-")

# -------------------------------------------
# AI PREDICTION
# -------------------------------------------
st.subheader("Prediksi Status Sistem")

if None not in (suhu, asap, cahaya):
    X = [[suhu, asap, cahaya]]
    pred = model.predict(X)[0]

    if pred == "BAHAYA":
        st.error(f" Status: {pred}")
        client.publish("alat/buzzer/sic", "ON")
    else:
        st.success(f" Status: {pred}")
        client.publish("alat/buzzer/sic", "OFF")

else:
    st.info("Menunggu data sensor masuk...")

st.caption("Dashboard berjalan realtime menggunakan MQTT + Machine Learning")
