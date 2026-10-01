# Deploying CoachAI on Render (free tier)

A one-time setup (~10 minutes), then the demo is online at a stable URL and
**auto-redeploys every time someone pushes to `main`** — which means small UI
changes can be previewed without running anything locally.

## What you need

- A Render account (free): https://render.com — sign up with the **GitHub account that has access to this repo**
- A DeepSeek API key (the project key, or your own)

## Steps

1. **Create the service**
   - Render dashboard → **New** → **Web Service**
   - Connect GitHub → pick `12345666ddwa/coachai-mvp`
   - Render reads `render.yaml` automatically (Blueprint). If asked, choose the free plan.

2. **Set the API key**
   - In the service's **Environment** tab, add:
     - `DEEPSEEK_API_KEY` = your DeepSeek key
   - (Everything else is already in `render.yaml`.)

3. **Deploy**
   - Click **Deploy**. First build takes ~5-8 minutes (installs deps + pre-downloads the embedding model).

4. **Open the URL**
   - Render gives you `https://coachai-demo-XXXX.onrender.com` — that's the live demo for everyone.

## Notes and quirks (free tier)

| Topic | Behaviour |
|---|---|
| Cold start | After ~15 min without visits the instance sleeps; the next visit takes ~1-3 min to wake. Open it once before a demo/pitch. |
| First markings | The first AI call after a cold start can take 30-60 s; subsequent ones are normal. |
| RAG index | The vector DB (`data/chroma_db/`) is committed, so retrieval works out of the box. |
| Audio transcription | `faster-whisper` is installed, but very long recordings are impractical on the free instance; paste transcripts instead when possible. |
| Secrets | Never put keys in the repo. Keys live in Render's Environment tab only. |

## Updating the deployment

Any push to `main` triggers an automatic redeploy (2-4 min). To preview UI tweaks:

1. Make the change (locally or on GitHub web editor)
2. Push to `main`
3. Render rebuilds; refresh your demo URL

## Troubleshooting

- **Build fails on pip** → check the failing package in Render logs; usually a version pin issue.
- **App starts but model calls error** → check `DEEPSEEK_API_KEY` is set in Environment (not just locally).
- **Loading forever after deploy** → watch the Render logs `Your service is live` line; then open the URL itself (not just the Render dashboard preview).
