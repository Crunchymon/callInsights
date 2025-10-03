import streamlit as st
import requests
import time
import tempfile
from fpdf import FPDF
import google.generativeai as genai
import re
import unicodedata

# Set up AssemblyAI and Gemini
ASSEMBLYAI_API_KEY = st.secrets["ASSEMBLYAI_API_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.5-pro")

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
        "language_detection": True,
        "speaker_labels": True,
        "sentiment_analysis": True,
        "entity_detection": True,
        "auto_highlights": True
    }
    response = requests.post(ASSEMBLYAI_TRANSCRIBE_URL, headers=headers, json=data)
    response.raise_for_status()
    transcript_id = response.json()["id"]

    polling_url = f"{ASSEMBLYAI_TRANSCRIBE_URL}/{transcript_id}"
    while True:
        poll_response = requests.get(polling_url, headers=headers)
        status = poll_response.json()
        if status["status"] == "completed":
            return status
        elif status["status"] == "failed":
            raise Exception("Transcription failed")
        time.sleep(3)

# Clean output for PDF

def insights_cleaner(insights: str) -> str:
    # Normalize Unicode (removes accents, emojis)
    cleaned = unicodedata.normalize("NFKD", insights).encode("ASCII", "ignore").decode("ASCII")

    # Remove emojis and bullet-like symbols
    cleaned = re.sub(r"[*•→►▪️🔹⚫🔸❖✅🔥💡➡️➤➔]", "", cleaned)

    # Normalize Windows/mac line endings to Unix
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # Split by double newlines to preserve paragraph structure
    paragraphs = re.split(r"\n{2,}", cleaned)

    formatted_paragraphs = []
    for para in paragraphs:
        # Remove excess spaces in each line, then join the lines in a paragraph
        lines = para.split("\n")
        cleaned_lines = [re.sub(r"\s+", " ", line).strip() for line in lines if line.strip()]
        if cleaned_lines:
            formatted_paragraphs.append(" ".join(cleaned_lines))

    # Join paragraphs with double newlines to preserve spacing in PDF
    final_text = "\n\n".join(formatted_paragraphs).strip()

    return final_text


# Generate insights using Gemini
def generate_insights(transcript):
    prompt = f"""
    This is a sales call transcript response from assembly AI with labels of speakers present as well it can be a mix of hindi and english. Analyze it and provide:

    1. Identify key discussion points and objections
    2. Rate the sales agent's performance (score out of 5) (e.g., tone, pitch, flow, handling objections)
    3. Generate next actionables (follow-up tasks, customer interest level, etc.)
    4. explain the evaluation criteria and logic used for generating actionables
    5. Keep it short and concise
    
    Transcript:
    {transcript}
    pay special attention to entities in the transcirpt {transcript["entities"]} and sentiment analysis {transcript["sentiment_analysis_results"]} 
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
    uploaded_file = st.file_uploader("Upload audio file", type=["mp3", "wav", "m4a", "aac", "ogg", "flac", "webm", "mp4", "mov","amr"])
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

        st.subheader("Transcript:")
        # st.write(transcript)
        # for i in transcript["utterances"]:
        #     st.write(f"Speaker {i['speaker']} : {i['text']}")
        st.write(transcript["text"])

    with st.spinner("Generating Insights with Gemini..."):
        insights = (generate_insights(transcript))
        st.subheader("Insights")
        st.write(insights)

        pdf_path = "call_insights.pdf"
        create_pdf(insights_cleaner(insights), pdf_path)

        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF", f, file_name="call_report.pdf")
