# Multi PDF Bot

Upload one or more PDFs, ask a question, and get a written answer read aloud. The site is a Flask app that reads the PDFs, asks OpenAI for an answer, and speaks it with ElevenLabs.

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put your keys in `.env`:

```bash
OPENAI_API_KEY=sk-...
ELEVEN_API_KEY=...
```

Then start the app and open http://localhost:5000:

```bash
python app.py
```

The page loads without keys. Asking a question needs both keys.

## Deploy on Vercel

The app is set up for Vercel’s Flask runtime. `app.py` exports `app`, static files live in `public/`, and `vercel.json` gives the function enough time to read a PDF, call OpenAI, and request the voice.

1. Import this GitHub repo in [Vercel](https://vercel.com/new).
2. Add these environment variables for Production and Preview:
   - `OPENAI_API_KEY`
   - `ELEVEN_API_KEY`
3. Deploy. Vercel installs `requirements.txt` and serves the Flask app.

Or use this link, which asks for the two keys during import:

[Deploy with Vercel](https://vercel.com/new/clone?repository-url=https://github.com/Nancy20052020/Mutli_PDF_BOT&env=OPENAI_API_KEY,ELEVEN_API_KEY&project-name=multi-pdf-bot&envDescription=OpenAI%20and%20ElevenLabs%20keys)

Optional variables:

| Name | Default | Purpose |
| --- | --- | --- |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `ELEVEN_VOICE_ID` | `21m00Tcm4TlvDq8ikWAM` | ElevenLabs voice |
| `ELEVEN_MODEL` | `eleven_multilingual_v2` | Speech model |

## Limits

- Up to 5 PDFs, 4 MB each. Vercel’s request body limit is about 4.5 MB, so keep uploads small.
- Only PDFs with selectable text work. Scanned pages need OCR first.
- The model sees about the first 12,000 characters of extracted text.
- Spoken answers are capped around 2,500 characters. The full written answer is still shown.
- A question can take a few seconds. `vercel.json` allows the function to run for up to 60 seconds.

## Project layout

```
app.py                 Flask app and /api/query
templates/index.html   Page
public/static/         CSS, JavaScript, and the book photo
requirements.txt       Python dependencies
vercel.json            Function duration and bundled templates
```
