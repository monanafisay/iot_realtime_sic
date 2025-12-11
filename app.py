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
st.set_page_config(page_title="IoT ESP32 Das_
