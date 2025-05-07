import streamlit as st
import requests
import time
import tempfile
import os
from fpdf import FPDF
import google.generativeai as genai
import re
import unicodedata

# Set up AssemblyAI and Gemini
ASSEMBLYAI_API_KEY = st.secrets["ASSEMBLYAI_API_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

headers = {
    "authorization": ASSEMBLYAI_API_KEY,
    "content-type": "application/json"
}
ASSEMBLYAI_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLYAI_TRANSCRIBE_URL = "https://api.assemblyai.com/v2/transcript"

# Upload file to AssemblyAI
def upload_to_assemblyai(file_path):
    with open(file_path, "rb") as f:
        response = requests.post(ASSEMBLYAI_UPLOAD_URL, headers=headers, data=f)
    response.raise_for_status()
    return response.json()["upload_url"]

# Transcribe via AssemblyAI using file or external URL
def transcribe_audio_assemblyai(file_path=None, external_url=None):
    if file_path:
        audio_url = upload_to_assemblyai(file_path)
    elif external_url:
        audio_url = external_url
    else:
        raise ValueError("Must provide file_path or external_url")

    data = {
        "audio_url": audio_url,
        "language_detection": True
    }
    response = requests.post(ASSEMBLYAI_TRANSCRIBE_URL, headers=headers, json=data)
    response.raise_for_status()
    transcript_id = response.json()["id"]

    polling_url = f"{ASSEMBLYAI_TRANSCRIBE_URL}/{transcript_id}"
    while True:
        poll_response = requests.get(polling_url, headers=headers)
        status = poll_response.json()
        if status["status"] == "completed":
            return status["text"]
        elif status["status"] == "failed":
            raise Exception("Transcription failed")
        time.sleep(3)

# Clean output for PDF


def insights_cleaner(insights: str) -> str:
    # Normalize Unicode characters to ASCII (removes accents/symbols)
    cleaned = unicodedata.normalize("NFKD", insights).encode("ASCII", "ignore").decode("ASCII")

    # Remove bullet points, emojis, and other unsafe characters
    cleaned = re.sub(r"[*•→►▪️🔹⚫🔸❖]", "", cleaned)

    # Replace multiple newlines with a single newline
    cleaned = re.sub(r"\n+", "\n", cleaned)

    # Remove any control characters
    cleaned = re.sub(r"[\x00-\x1F\x7F]", "", cleaned)

    # Strip excessive spaces from beginning/end
    cleaned = cleaned.strip()

    return cleaned

# Generate insights using Gemini
def generate_insights(transcript_1, transcript_2):
    prompt = f"""
    This is a sales call transcript it can be a mix of hindi and english (both the hindi and english transcripts are provided). Analyze it and provide:

    1. Identify key discussion points and objections
    2. Rate the sales agent's performance (e.g., tone, pitch, flow, handling objections)
    3. Generate next actionables (follow-up tasks, customer interest level, etc.)
    4. explain the evaluation criteria and logic used for generating actionables
    5. Keep it short and concise

    DO NOT USE ANY SPECIAL CHARACTERS OR BULLET POINTS IN THE RESPONSE THAT MAY CAUSE ISSUES WITH THE PDF GENERATION USING FPDF
    Transcript:
    {transcript_1}
    {transcript_2}
    """
    response = gemini_model.generate_content(prompt)
    return response.text

# Create PDF
def create_pdf(text, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        pdf.multi_cell(0, 10, line)
    pdf.output(output_path)

# === Streamlit UI ===

st.title("AI-Powered Call Insights Generator")

input_mode = st.radio("Select Input Type", ("Upload File", "Audio URL"))
transcript = ""

uploaded_file = None
audio_url = None

if input_mode == "Upload File":
    uploaded_file = st.file_uploader("Upload audio file", type=["mp3", "wav", "m4a"])
else:
    audio_url = st.text_input("Paste public audio URL")

if (uploaded_file and input_mode == "Upload File") or (audio_url and input_mode == "Audio URL"):
    with st.spinner("Transcribing..."):
        if input_mode == "Upload File":
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            transcript = transcribe_audio_assemblyai(file_path=tmp_path)
        else:
            transcript = transcribe_audio_assemblyai(external_url=audio_url)

        st.subheader("Transcript")
        st.text(transcript)

    with st.spinner("Generating Insights with Gemini..."):
        insights = insights_cleaner(generate_insights(transcript, ""))
        st.subheader("Insights")
        st.text(insights)

        pdf_path = "call_insights.pdf"
        create_pdf(insights, pdf_path)

        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF", f, file_name="call_report.pdf")
