import streamlit as st
import whisper
import tempfile
import google.generativeai as genai
import os
from fpdf import FPDF


# Add current directory to PATH so Whisper finds ./ffmpeg
os.environ["PATH"] = os.getcwd() + os.pathsep + os.environ["PATH"]


import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# Load models once and store them globally
@st.cache_resource
def load_whisper_models():
    return {
        "base": whisper.load_model("base"),
        "small": whisper.load_model("small"),
        "medium": whisper.load_model("medium"),
    }

whisper_models = load_whisper_models()

# Updated transcribe_audio function
def transcribe_audio(file_path, model_key, language):
    model = whisper_models[model_key]
    result = model.transcribe(file_path, language=language)
    return result["text"]


def generate_insights(transcript_1,transcript_2):
    prompt = f"""
    This is a sales call transcript it can be a mix of hindi and english (both the hindi and english transcripts are provided). Analyze it and provide:

    1. Identify key discussion points and objections
    2. Rate the sales agent's performance (e.g., tone, pitch, flow, handling objections)
    3. Generate next actionables (follow-up tasks, customer interest level, etc.)
    4. explain the  evaluation criteria and logic used for generating actionables
    5. Keep it short and concise

    DO NOT USE ANY SPECIAL CHARACTERS OR BULLET POINTS IN THE RESPONSE THAT MAY CAUSE ISSUES WITH THE PDF GENERATION USING FPDF
    Transcript:
    {transcript_1}
    {transcript_2}
    """
    response = gemini_model.generate_content(prompt)
    return response.text


def insights_cleaner(insights):
    new_reponse = ""
    for i in insights:
        if i!="*":
            new_reponse += i
    return new_reponse

def create_pdf(text, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    lines = text.split("\n")
    for line in lines:
        pdf.multi_cell(0, 10, line)

    pdf.output(output_path)





# Streamlit UI
mode = st.radio("Choose the transcript mode:", ("Fast (But with low Accuracy)", "Balanced", "Accurate (But Slow)"), index=1)
st.title("AI-Powered Call Insights Generator")

uploaded_file = st.file_uploader("Upload audio file", type=["mp3", "wav", "m4a"])
st.text("Your current Chosen Transcript mode:")
st.text(mode)
if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    with st.spinner("Transcribing..."):
        if mode == "Fast (But with low Accuracy)":
            transcript_base_english = transcribe_audio(tmp_path,"base","english")
            transcript_base_hindi = transcribe_audio(tmp_path,"base","hindi")
        elif mode == "Balanced":
            transcript_base_english = transcribe_audio(tmp_path,"medium","english")
            transcript_base_hindi = transcribe_audio(tmp_path,"small","hindi")
        else:
            transcript_base_english = transcribe_audio(tmp_path,"medium","english")
            transcript_base_hindi = transcribe_audio(tmp_path,"medium","hindi")

    
        st.subheader("Transcript")
        st.text(transcript_base_english)
        st.text(transcript_base_hindi)

    with st.spinner("Generating Insights with Gemini..."):
        insights = insights_cleaner(generate_insights(transcript_base_english,transcript_base_hindi))
        st.subheader("Insights")
        st.text(insights)

        # Generate PDF
        pdf_path = "call_insights.pdf"
        create_pdf(insights, pdf_path)

        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF", f, file_name="call_report.pdf")