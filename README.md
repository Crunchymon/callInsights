# Automated Call Analysis Pipeline ✨

**Live Demo:** [https://crunchymon-callinsights-app-iasu4g.streamlit.app/](https://crunchymon-callinsights-app-iasu4g.streamlit.app/)

## Project Overview

This is a full-stack web application that automates the analysis of sales call recordings. The system orchestrates multiple AI services to transcribe, enrich, and summarize call data, delivering actionable insights to a user-friendly dashboard and generating a professional PDF report. It's designed to help sales managers quickly understand call outcomes and agent performance without manual review.

## Key Features

* **Multi-Source Audio Ingestion:** Accepts audio data via direct file upload (MP3, WAV, etc.) or from a public URL, handling temporary file storage and secure data transfer to the processing backend.

* **Asynchronous Transcription & Enrichment Pipeline:** Leverages the AssemblyAI API to perform speaker diarization (identifying who is speaking), sentiment analysis, and key entity detection. Implements a robust **polling mechanism** to handle the asynchronous nature of the transcription job, waiting for the task to complete before proceeding.

* **Generative AI-Powered Summarization:** Takes the structured, enriched transcript from AssemblyAI and pipes it into a Google Gemini model. A custom-engineered prompt instructs the model to perform a targeted analysis, including:
    * Identifying key discussion points and customer objections.
    * Scoring sales agent performance based on tone and flow.
    * Defining actionable next steps and follow-up tasks.

* **Automated PDF Report Generation:** Includes a data cleaning module using regex and Unicode normalization to format the AI-generated insights into a clean, professional PDF report, which is made available for users to download.

## Tech Stack

* **Language:** Python
* **Web Framework:** Streamlit
* **Core Services:** AssemblyAI API (for transcription & enrichment), Google Gemini API (for generative analysis)
* **Libraries:** Requests, FPDF

## Installation & Usage

1.  Clone the repository:
    ```bash
    git clone [https://github.com/yourusername/CallInsights.git](https://github.com/yourusername/CallInsights.git)
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the app:
    ```bash
    streamlit run app.py
    ```
