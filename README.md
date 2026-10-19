# Multi PDF Bot

Upload one or more PDFs, ask a question, and get a written answer read aloud. The Flask app reads the PDFs, asks OpenAI for an answer, and speaks it with ElevenLabs.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put your keys in `.env`. They stay on your machine and are not part of the repo:

```bash
OPENAI_API_KEY=sk-...
ELEVEN_API_KEY=...
```

Start the app and open http://localhost:5000:

```bash
python app.py
```

The page loads without keys. Asking a question needs both keys.

Optional settings in `.env`:

| Name | Default | Purpose |
| --- | --- | --- |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `ELEVEN_VOICE_ID` | `21m00Tcm4TlvDq8ikWAM` | ElevenLabs voice |
| `ELEVEN_MODEL` | `eleven_multilingual_v2` | Speech model |

## Limits

- Up to 5 PDFs, 4 MB each.
- Only PDFs with selectable text work. Scanned pages need OCR first.
- The model sees about the first 12,000 characters of extracted text.
- Spoken answers are capped around 2,500 characters. The full written answer is still shown.

## Project layout

```
app.py                 Flask app and /api/query
templates/index.html   Page
static/                CSS, JavaScript, and the book photo
requirements.txt       Python dependencies
```
