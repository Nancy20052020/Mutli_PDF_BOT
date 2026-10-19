import io
import unittest
from pathlib import Path
from unittest import mock

from app import app

PDF = (Path(__file__).parent / "fixtures" / "notes.pdf").read_bytes()


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.env = mock.patch.dict("os.environ", {"OPENAI_API_KEY": "", "ELEVEN_API_KEY": ""}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_home_and_assets(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"Ask your documents", home.data)
        self.assertEqual(self.client.get("/static/styles.css").status_code, 200)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)
        self.assertEqual(self.client.get("/static/pic1_bot.jpeg").status_code, 200)

    def test_health_without_keys(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["ok"])
        self.assertFalse(body["openai"])
        self.assertFalse(body["elevenlabs"])

    def test_query_requires_pdf_and_question(self):
        missing_pdf = self.client.post("/api/query", data={"query": "What?"})
        self.assertEqual(missing_pdf.status_code, 400)

        missing_question = self.client.post(
            "/api/query",
            data={"pdfs": (io.BytesIO(PDF), "notes.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(missing_question.status_code, 400)

    def test_rejects_non_pdf(self):
        response = self.client.post(
            "/api/query",
            data={
                "pdfs": (io.BytesIO(b"hello"), "notes.txt"),
                "query": "What does it say?",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not a PDF", response.get_json()["error"])

    def test_valid_pdf_reaches_key_check(self):
        response = self.client.post(
            "/api/query",
            data={
                "pdfs": (io.BytesIO(PDF), "notes.pdf"),
                "query": "What is the capital of France?",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENAI_API_KEY", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
