import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, make_response
from PyPDF2 import PdfReader
import openai
import requests
from io import BytesIO
import base64

load_dotenv()  # Load environment variables from .env

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.after_request
def add_cors_headers(response):
    if request.path.startswith('/api/'):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

@app.route('/api/query', methods=['OPTIONS'])
def handle_options():
    response = make_response()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

# Read API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

if not OPENAI_API_KEY or not ELEVEN_API_KEY:
    raise RuntimeError("API keys not found in environment variables. Set OPENAI_API_KEY and ELEVEN_API_KEY in your .env file.")

VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def extract_text_from_pdfs(files):
    full_text = ""
    for f in files:
        reader = PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    return full_text

def generate_speech_elevenlabs(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }
    json_data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.75
        }
    }
    response = requests.post(url, headers=headers, json=json_data)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"ElevenLabs TTS API error: {response.status_code} {response.text}")

@app.route('/api/query', methods=['POST'])
def handle_query():
    if 'pdfs' not in request.files:
        return jsonify({"error": "No PDF files"}), 400

    files = request.files.getlist('pdfs')
    query = request.form.get('query', '').strip()
    if not query:
        return jsonify({"error": "No query provided"}), 400

    pdf_text = extract_text_from_pdfs(files)
    if not pdf_text:
        return jsonify({"error": "No text could be extracted from PDF(s)"}), 400

    prompt = (
        f"Use the following text from PDF documents to answer the question.\n\n"
        f"Text:\n{pdf_text[:3000]}\n\nQuestion: {query}\nAnswer:"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant answering questions based on PDF text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({"error": f"OpenAI API error: {str(e)}"}), 500

    try:
        audio_content = generate_speech_elevenlabs(answer)
        audio_b64 = base64.b64encode(audio_content).decode('utf-8')
        return jsonify({
            "answer": answer,
            "audio_base64": audio_b64
        })
    except Exception as ex:
        return jsonify({
            "answer": answer,
            "audio_base64": None,
            "tts_error": str(ex)
        })

@app.route('/')
def index():
    return render_template('index.html')
app.run(debug=True, port=5000)
