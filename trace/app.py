"""Trace: reverse image search on top of Google Cloud Vision Web Detection."""
import base64, html, io, os, re, threading
from datetime import date
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from PIL import Image, ImageOps

load_dotenv()
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
VISION_URL = "https://vision.googleapis.com/v1/images:annotate"
_lock, _usage = threading.Lock(), {"day": date.today(), "n": 0}


class UserError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


@app.errorhandler(UserError)
def user_error(e):
    return jsonify(error=str(e)), e.status


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="That file is over 20 MB. Try a smaller photo."), 413


def take_quota():
    """Cap searches per day so a stray visitor can't run up your Google bill."""
    limit = int(os.getenv("DAILY_LIMIT", "200"))
    with _lock:
        if _usage["day"] != date.today():
            _usage.update(day=date.today(), n=0)
        if _usage["n"] >= limit:
            raise UserError(f"Daily limit of {limit} searches reached. Raise DAILY_LIMIT in .env to continue.", 429)
        _usage["n"] += 1


def http_url(u):
    p = urlparse(u or "")
    return u if p.scheme in ("http", "https") and p.hostname else None


def clean(text):
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def encode_upload(f):
    try:
        img = ImageOps.exif_transpose(Image.open(f.stream)).convert("RGB")
    except Exception:
        raise UserError("That file isn't an image Trace can read. Try a JPG, PNG or WebP.")
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def web_detect(image):
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise UserError("GOOGLE_API_KEY is missing. Add it to your .env file (see the README).", 500)
    body = {"requests": [{"image": image, "features": [{"type": "WEB_DETECTION", "maxResults": 20}]}]}
    try:
        r = requests.post(VISION_URL, params={"key": key}, json=body, timeout=30)
        data = r.json()
    except (requests.RequestException, ValueError):
        raise UserError("Couldn't get a response from Google Cloud Vision. Check your connection and try again.", 502)
    err = data.get("error") or (data.get("responses") or [{}])[0].get("error")
    if err:
        hint = " Check that the Vision API is enabled, billing is on, and your key allows the Vision API." if r.status_code == 403 else ""
        raise UserError(f"Google said: {err.get('message', 'unknown error')}{hint}", 502)
    return data["responses"][0].get("webDetection", {})


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/search")
def search():
    upload, link = request.files.get("image"), (request.form.get("image_url") or "").strip()
    if upload:
        image = {"content": encode_upload(upload)}
    elif http_url(link):
        image = {"source": {"imageUri": link}}
    else:
        raise UserError("Add a photo, or paste a full image link starting with https://.")
    take_quota()
    web = web_detect(image)

    pages = []
    for p in web.get("pagesWithMatchingImages", []):
        if http_url(p.get("url")):
            host = urlparse(p["url"]).hostname.removeprefix("www.")
            pages.append({"url": p["url"], "domain": host, "title": clean(p.get("pageTitle")) or host,
                          "exact": bool(p.get("fullMatchingImages"))})
    urls = lambda k: [i["url"] for i in web.get(k, []) if http_url(i.get("url"))]
    entities = sorted(web.get("webEntities", []), key=lambda e: -e.get("score", 0))
    return jsonify(
        best_guess=[b["label"] for b in web.get("bestGuessLabels", [])],
        topics=[e["description"] for e in entities if e.get("description")][:10],
        pages=pages, exact=urls("fullMatchingImages"), similar=urls("visuallySimilarImages"),
    )


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")))
