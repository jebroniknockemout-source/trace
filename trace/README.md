# Trace

A small reverse image search app. Add a photo (or paste an image link) and Trace shows the pages where that image appears online, exact copies, visually similar images, and the topics Google associates with them. It uses the **Google Cloud Vision API's Web Detection** feature.

It does not use face detection or face recognition. If a photo of a public figure has been published, the pages that contain it will name them. If the image isn't online, you get no matches.

## Setup

You need Python 3.9+ and your own Google Cloud API key.

1. In the [Google Cloud console](https://console.cloud.google.com), create a project.
2. Enable the **Cloud Vision API** (APIs & Services > Library).
3. Turn on billing for the project. Vision requires a billing account even when you stay inside the free tier.
4. Create an API key (APIs & Services > Credentials) and restrict it to the Cloud Vision API.
5. Optional but wise: set a budget alert under Billing.

```bash
git clone <your-repo-url> && cd trace
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                # then paste your key into .env
python app.py
```

Open http://127.0.0.1:5000. To use it from your phone on the same Wi-Fi, set `HOST=0.0.0.0` in `.env` and open `http://<your-computer-ip>:5000`.

## Cost

Google gives 1,000 Web Detection requests free each month. After that it is about $3.50 per 1,000 (see [Vision pricing](https://cloud.google.com/vision/pricing)). New Google Cloud customers also get trial credit. Every person running Trace pays for their own key.

`DAILY_LIMIT` (default 200) caps searches per day as a safety net.

## Notes

- Trace has no login. Keep it on your own machine or network, and don't put it on the public internet with your key.
- Photos you search are sent to Google. Don't search images you wouldn't want Google to receive.
- Results come from Google's Web Detection and won't match the Google Lens app exactly.
