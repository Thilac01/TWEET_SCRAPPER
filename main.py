from flask import Flask, render_template, request, Response, jsonify, send_file
from flask_cors import CORS
import threading, queue, time, json, os
from scraper.logger import get_queue_logger
from scraper.scraper import TweetScraper

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# Shared resources
LOG_Q = queue.Queue()
logger = get_queue_logger(LOG_Q)
SCRAPER_THREAD = None
SCRAPER_OBJ = None
TWEETS = []  # shared live tweets list (append-only)
SETTINGS = {}
# load settings
with open(os.path.join("config", "settings.json"), "r") as f:
    SETTINGS = json.load(f)

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/login", methods=["POST"])
def login():
    # we don't need to spawn driver here; login happens inside scraper run or we can prelaunch
    logger.info("Request: login (noop) - cookies will be used when scraping starts")
    return jsonify({"status":"ok", "message":"Ready: cookies will be used when starting scraper."})

@app.route("/start", methods=["POST"])
def start_scrape():
    global SCRAPER_THREAD, SCRAPER_OBJ, TWEETS
    if SCRAPER_THREAD and SCRAPER_THREAD.is_alive():
        return jsonify({"status":"error", "message":"Scraper already running"}), 400

    payload = request.json or {}
    keyword = payload.get("keyword", "")
    max_tweets = int(payload.get("max_tweets", SETTINGS.get("max_tweets_default", 100)))
    cookies = payload.get("cookies", None)

    # clear previous tweets
    TWEETS = []
    # create scraper
    scraper = TweetScraper(keyword=keyword, max_tweets=max_tweets, settings=SETTINGS, log_queue=LOG_Q, tweets_list=TWEETS)
    SCRAPER_OBJ = scraper
    SCRAPER_THREAD = threading.Thread(target=scraper.run, kwargs={"cookies": cookies}, daemon=True)
    SCRAPER_THREAD.start()
    logger.info(f"Started scraper for '{keyword}' max {max_tweets}")
    return jsonify({"status":"ok", "message":"Scraper started"})

@app.route("/stop", methods=["POST"])
def stop_scrape():
    global SCRAPER_OBJ
    if SCRAPER_OBJ:
        SCRAPER_OBJ.stop()
        logger.info("Stop requested for scraper")
        return jsonify({"status":"ok", "message":"Stop requested"})
    return jsonify({"status":"error","message":"No scraper running"}), 400

@app.route("/stream")
def stream():
    def event_stream():
        while True:
            try:
                msg = LOG_Q.get(timeout=0.5)
                yield f"data: {json.dumps(msg)}\n\n"
            except Exception:
                # heartbeat
                yield ":\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/data")
def data():
    # return live tweets
    return jsonify({"count": len(TWEETS), "tweets": TWEETS})

@app.route("/download/csv")
def download_csv():
    path = os.path.join("downloads", "tweets.csv")
    if not os.path.exists(path):
        return jsonify({"status":"error","message":"No CSV data yet"}), 404
    return send_file(path, as_attachment=True)

@app.route("/download/json")
def download_json():
    path = os.path.join("downloads", "tweets.json")
    if not os.path.exists(path):
        return jsonify({"status":"error","message":"No JSON data yet"}), 404
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    app.run(host=SETTINGS.get("host", "0.0.0.0"), port=int(SETTINGS.get("port", 8000)), debug=False, threaded=True)
