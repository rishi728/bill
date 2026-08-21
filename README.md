# Pathology Lab GST Invoice Generator

Web app to create GST invoices for a pathology lab and download them as PDF.

## Deploy to Render

1. Create a **new GitHub repo** and upload these 4 files to the **root** of the repo
   (not inside any folder):
   - `app.py`
   - `requirements.txt`
   - `render.yaml`
   - `.gitignore`

2. Go to [render.com](https://render.com) -> **New** -> **Web Service** -> connect the repo.

3. Render reads `render.yaml` automatically. If it asks manually, use:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

4. Click **Deploy**. You get a live URL in ~2 minutes.

5. Open the URL -> **Settings** tab -> fill in lab name, address, PAN, bank details -> **Save**.

## Checking it works

Visit `https://your-app.onrender.com/health` — it should return `{"status": "ok", ...}`.

## Notes

- PDFs are generated **in the browser** (jsPDF), so the server stays lightweight.
- Data is stored in `data.json` next to `app.py`.
- On Render's **free plan the disk is ephemeral** — bill history resets whenever the
  service restarts or redeploys. Settings and the test master list will need re-entering
  after a restart. To make data permanent, attach a Render Persistent Disk (paid plan)
  or switch storage to a database.
- Free plan sleeps after 15 min idle; first visit then takes ~30s to wake.

## Run locally

```bash
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```
