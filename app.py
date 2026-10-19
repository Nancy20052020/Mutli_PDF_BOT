import base64
import os
import re
from io import BytesIO

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

load_dotenv()

app = Flask(
    __name__,
    static_folder="public/static",
    template_folder="templates",
)

MAX_FILES = 5
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_QUERY_CHARS = 1000
MAX_PROMPT_CHARS = 12000
MAX_TTS_CHARS = 2500
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


def _clean(value):
    return (value or "").strip()


def openai_key():
    return _clean(os.getenv("OPENAI_API_KEY"))


def eleven_key():
    return _clean(os.getenv("ELEVEN_API_KEY"))


def public_error(exc):
    text = str(exc)
    text = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-…", text)
    text = re.sub(r"(?i)(xi-api-key['\"]?\s*[:=]\s*)\S+", r"\1…", text)
    return text[:300]


def extract_text_from_pdfs(files):
    chunks = []
    problems = []
    for storage in files:
        name = storage.filename or "document.pdf"
        data = storage.read()
        if not data:
            problems.append(f"{name} is empty")
            continue
        if len(data) > MAX_FILE_BYTES:
            problems.append(f"{name} is larger than 4 MB")
            continue
        if not data.startswith(b"%PDF"):
            problems.append(f"{name} is not a PDF")
            continue
        try:
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                problems.append(f"{name} is password protected")
                continue
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text.strip())
        except PdfReadError:
            problems.append(f"{name} could not be read")
            continue
        except Exception:
            app.logger.exception("Failed to read %s", name)
            problems.append(f"{name} could not be read")
            continue
        if not pages:
            problems.append(f"{name} has no selectable text (scanned pages need OCR)")
            continue
        chunks.append(f"--- {name} ---\n" + "\n".join(pages))
    return "\n\n".join(chunks), problems


def generate_speech(text):
    voice_id = _clean(os.getenv("ELEVEN_VOICE_ID")) or DEFAULT_VOICE_ID
    model_id = _clean(os.getenv("ELEVEN_MODEL")) or "eleven_multilingual_v2"
    spoken = text if len(text) <= MAX_TTS_CHARS else text[:MAX_TTS_CHARS].rsplit(" ", 1)[0]
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": eleven_key(),
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": spoken,
            "model_id": model_id,
            "voice_settings": {"stability": 0.7, "similarity_boost": 0.75},
        },
        timeout=45,
    )
    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs returned {response.status_code}")
    return response.content, spoken != text


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "ok": bool(openai_key() and eleven_key()),
        "openai": bool(openai_key()),
        "elevenlabs": bool(eleven_key()),
    })


@app.route("/api/query", methods=["POST"])
def handle_query():
    files = request.files.getlist("pdfs")
    files = [item for item in files if item and item.filename]
    if not files:
        return jsonify({"error": "Upload at least one PDF."}), 400
    if len(files) > MAX_FILES:
        return jsonify({"error": f"Upload up to {MAX_FILES} PDFs at a time."}), 400

    query = request.form.get("query", "").strip()
    if not query:
        return jsonify({"error": "Enter a question."}), 400
    if len(query) > MAX_QUERY_CHARS:
        return jsonify({"error": f"Keep the question under {MAX_QUERY_CHARS} characters."}), 400

    pdf_text, problems = extract_text_from_pdfs(files)
    if not pdf_text:
        detail = " ".join(problems) if problems else "No text could be extracted."
        return jsonify({"error": detail}), 400

    if not openai_key() or not eleven_key():
        return jsonify({
            "error": "Add OPENAI_API_KEY and ELEVEN_API_KEY in the environment, then try again.",
        }), 503

    clipped = pdf_text[:MAX_PROMPT_CHARS]
    prompt = (
        "Answer the question using only the PDF text below. "
        "If the text does not contain the answer, say so.\n\n"
        f"Text:\n{clipped}\n\nQuestion: {query}"
    )

    try:
        client = OpenAI(api_key=openai_key())
        response = client.chat.completions.create(
            model=_clean(os.getenv("OPENAI_MODEL")) or "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You answer questions about uploaded PDFs. Be concise and accurate.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
        )
        answer = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        app.logger.exception("OpenAI request failed")
        return jsonify({"error": f"OpenAI request failed. {public_error(exc)}"}), 502

    if not answer:
        return jsonify({"error": "The model returned an empty answer."}), 502

    payload = {"answer": answer, "audio_base64": None, "audio_note": None, "notices": problems}
    try:
        audio, truncated = generate_speech(answer)
        payload["audio_base64"] = base64.b64encode(audio).decode("ascii")
        if truncated:
            payload["audio_note"] = "The spoken answer is shortened so it stays within the voice limit."
    except Exception as exc:
        app.logger.exception("Text-to-speech failed")
        payload["audio_note"] = f"The written answer is ready, but voice playback failed. {public_error(exc)}"

    return jsonify(payload)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
