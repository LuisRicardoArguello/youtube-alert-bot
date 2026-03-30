from flask import Flask, request, Response
import requests
import xml.etree.ElementTree as ET
import os

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")

LAST_VIDEO_ID = None

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=15,
    )

@app.route("/")
def home():
    return "Bot activo"

@app.route("/youtube-callback", methods=["GET", "POST"])
def youtube_callback():
    global LAST_VIDEO_ID

    challenge = request.args.get("hub.challenge")
    if challenge:
        return Response(challenge, status=200, mimetype="text/plain")

    raw_xml = request.data
    if not raw_xml:
        return Response("ok", status=200)

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015"
    }

    try:
        root = ET.fromstring(raw_xml)
        entry = root.find("atom:entry", ns)

        if entry is None:
            return Response("ok", status=200)

        video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
        channel_id = entry.findtext("yt:channelId", default="", namespaces=ns)
        title = entry.findtext("atom:title", default="Nuevo video", namespaces=ns)

        if not video_id or channel_id != CHANNEL_ID:
            return Response("ok", status=200)

        if video_id != LAST_VIDEO_ID:
            LAST_VIDEO_ID = video_id
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            send_telegram(f"🚨 Nuevo video detectado\n\n{title}\n{video_url}")

    except Exception as e:
        print("Error procesando XML:", e)

    return Response("ok", status=200)

@app.route("/subscribe", methods=["GET"])
def subscribe():
    callback_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/") + "/youtube-callback"
    topic_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

    data = {
        "hub.callback": callback_url,
        "hub.mode": "subscribe",
        "hub.topic": topic_url,
        "hub.verify": "async"
    }

    r = requests.post("https://pubsubhubbub.appspot.com/subscribe", data=data, timeout=20)
    return {
        "status_code": r.status_code,
        "text": r.text,
        "callback_url": callback_url,
        "topic_url": topic_url
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
