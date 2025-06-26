# -*- coding: utf-8 -*-
# process_docs_hybrid.py - V11 (Streamlined Metadata)

import os
import sys
import time
import json
import logging
import subprocess
import shutil
from datetime import datetime
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import google.generativeai as genai

# --- CONFIGURATION ---
INBOX_FOLDER = "/docs/inbox"
PROCESSED_FOLDER = "/docs/processed"
ERROR_FOLDER = "/docs/error"
WORKING_DIR = "/docs/tmp" 

HOST_TMP_PATH = os.getenv("HOST_TEMP_FOLDER")
API_KEY = os.getenv("GEMINI_API_KEY")
OUTPUT_LANGUAGE = os.getenv("OUTPUT_LANGUAGE", "both").lower()

if not HOST_TMP_PATH: raise ValueError("HOST_TEMP_FOLDER environment variable must be set.")
if not API_KEY: raise ValueError("GEMINI_API_KEY environment variable not found. Please set it.")

genai.configure(api_key=API_KEY)

def get_analysis_prompt(language, text_content):
    # ... (This function remains unchanged)
    base_instructions = f"""
You are an expert document analysis AI. Based *only* on the text provided, perform these actions:
1.  **Extract Document Date**: Find the main date of the document. Format it as . If no date is found, return null.
2.  **Identify Sender**: Determine the sender or primary entity.
"""
    if language == 'both':
        lang_instructions = """
3.  **Identify Document Type**: Determine the document type in both English and Quebecois French.
4.  **Generate Keywords**: Generate a concise list of 5-7 relevant keywords in BOTH English and Quebecois French.
5.  **Create Filename**: Propose a new filename using the Quebecois French document type and the extracted document date, like 'YYYY-MM-DD_Sender_DocTypeFR.pdf'.

Return ONLY a single, valid JSON object with the keys "doc_date", "doc_type" (as an object with "en" and "fr" keys), "sender", "tags" (as an object with "en" and "fr" keys), and "new_filename".
"""
    elif language == 'french':
        lang_instructions = """
3.  **Identify Document Type**: Determine the document type in Quebecois French. If it contains multiple words, separate them with hyphens.
4.  **Generate Keywords**: Generate a concise list of 5-7 relevant keywords in Quebecois French.
5.  **Create Filename**: Propose a new filename using the Quebecois French document type and the extracted document date, like 'YYYY-MM-DD_Sender_DocTypeFR.pdf'.

Return ONLY a single, valid JSON object with the keys "doc_date", "doc_type" (as a string), "sender", "tags" (as a list of strings), and "new_filename".
"""
    else: # English
        lang_instructions = """
3.  **Identify Document Type**: Determine the document type in English.
4.  **Generate Keywords**: Generate a concise list of 5-7 relevant keywords in English.
5.  **Create Filename**: Propose a new filename using the English document type and the extracted document date, like 'YYYY-MM-DD_Sender_DocTypeEN.pdf'.

Return ONLY a single, valid JSON object with the keys "doc_date", "doc_type" (as a string), "sender", "tags" (as a list of strings), and "new_filename".
"""
    return base_instructions + lang_instructions + f'\nDOCUMENT TEXT:\n"{text_content}"'

OCR_PROMPT = "Transcribe the full text content of this document. Do not summarize or add any extra commentary, just return the raw text."

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def run_command(command):
    # ... (This function remains unchanged)
    try:
        logging.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        logging.info("Command successful.")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with exit code {e.returncode}")
        logging.error(f"Stderr: {e.stderr}")
        logging.error(f"Stdout: {e.stdout}")
        raise

def get_text_from_gemini(pdf_path):
    # ... (This function remains unchanged)
    logging.info(f"Uploading {os.path.basename(pdf_path)} to Gemini for OCR...")
    gemini_file = genai.upload_file(path=pdf_path, display_name=os.path.basename(pdf_path))
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content([OCR_PROMPT, gemini_file])
        logging.info("Received OCR text from Gemini.")
        return response.text
    finally:
        genai.delete_file(gemini_file.name)
        logging.info(f"Temporary file {gemini_file.name} deleted from Google's servers.")

def get_analysis_from_gemini(text_content, language):
    # ... (This function remains unchanged)
    logging.info(f"Sending text to Gemini for analysis (Language: {language})...")
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    prompt = get_analysis_prompt(language, text_content)
    response = model.generate_content(prompt)
    logging.info("--- RAW ANALYSIS RESPONSE ---")
    logging.info(response.text)
    logging.info("--- END RAW ANALYSIS RESPONSE ---")
    try:
        json_start = response.text.find('{')
        json_end = response.text.rfind('}') + 1
        clean_response = response.text[json_start:json_end]
    except Exception as e:
        logging.error(f"Could not find a JSON object in the response: {e}")
        clean_response = ""
    if not clean_response: raise ValueError("Received an empty or non-JSON analysis response from Gemini.")
    return json.loads(clean_response)

def build_final_pdf(working_pdf_path, ocr_text, metadata):
    logging.info("Building final PDF and injecting metadata with OCRmyPDF...")
    pdf_filename = os.path.basename(working_pdf_path)
    
    # --- Prepare metadata strings (with robust None-checking) ---
    doc_type_val = metadata.get('doc_type') or 'Document'
    tags_val = metadata.get('tags') or []
    sender = metadata.get('sender') or 'Unknown'
    
    # Process doc_type
    if isinstance(doc_type_val, dict):
        title = f"{doc_type_val.get('en', '')} / {doc_type_val.get('fr', '')}"
    else:
        title = str(doc_type_val)
    
    subject = f"{sender} - {title}"

    # Process tags
    tags = []
    if isinstance(tags_val, dict):
        tags.extend(tags_val.get('en', []))
        tags.extend(tags_val.get('fr', []))
    elif isinstance(tags_val, list):
        tags.extend(tags_val)
    
    keywords = ", ".join(list(dict.fromkeys(tags)))

    # --- Create sidecar file ---
    sidecar_filename = f"{pdf_filename}.txt"
    sidecar_path_container = os.path.join(WORKING_DIR, sidecar_filename)
    with open(sidecar_path_container, 'w', encoding='utf-8') as f: f.write(ocr_text)

    output_pdf_path_container = os.path.join(WORKING_DIR, f"processed_{pdf_filename}")

    # --- Build OCRmyPDF command with all metadata flags ---
    command = [
        "docker", "run", "--rm",
        "-v", f"{HOST_TMP_PATH}:{WORKING_DIR}",
        "jbarlow83/ocrmypdf",
        "--output-type", "pdfa", "--redo-ocr",
        "--title", title,
        "--author", sender,
        "--subject", subject,
        "--keywords", keywords,
        "--sidecar", sidecar_path_container,
        working_pdf_path,
        output_pdf_path_container
    ]
    run_command(command)
    
    os.remove(sidecar_path_container)
    os.remove(working_pdf_path) 
    shutil.move(output_pdf_path_container, working_pdf_path)
    logging.info("Final PDF created successfully.")

def process_pdf(pdf_path_in_inbox):
    filename = os.path.basename(pdf_path_in_inbox)
    logging.info(f"--- Found new file: {filename} ---")
    
    working_path = os.path.join(WORKING_DIR, filename)

    try:
        shutil.move(pdf_path_in_inbox, working_path)
        logging.info(f"Moved {filename} to working directory: {WORKING_DIR}")

        # --- SMART CHECK ---
        full_text = extract_text_with_pdftotext(working_path)
        if full_text is None:
            logging.info("Falling back to Gemini for OCR.")
            full_text = get_text_from_gemini(working_path)

        if not full_text or not full_text.strip():
            raise ValueError("OCR resulted in empty text from all methods.")

        # --- ANALYSIS ---
        analysis_data = get_analysis_from_gemini(full_text, OUTPUT_LANGUAGE)

        # --- PDF PROCESSING ---
        # We always rebuild the PDF to inject metadata correctly.
        build_final_pdf(working_path, full_text, analysis_data)
        
        # --- FILENAME & DATE LOGIC ---
        doc_type_val = analysis_data.get('doc_type') or 'Document'
        doc_type_for_filename = ''
        if OUTPUT_LANGUAGE == 'english':
            doc_type_for_filename = str(doc_type_val) if not isinstance(doc_type_val, dict) else doc_type_val.get('en', 'Document')
        else: # Default to French for 'both' or 'french' modes
            if isinstance(doc_type_val, dict):
                doc_type_for_filename = doc_type_val.get('fr', 'Document')
            else:
                doc_type_for_filename = str(doc_type_val)

        sender = (analysis_data.get('sender') or 'Unknown').replace(' ', '_')
        doc_date = analysis_data.get('doc_date')
        
        if not doc_date:
            doc_date = datetime.now().strftime('%Y-%m-%d')
            logging.warning("No date found in document, using current date for filename.")

        safe_sender = "".join(c for c in sender if c.isalnum() or c in ('_','-')).rstrip()
        safe_doctype = "".join(c for c in doc_type_for_filename if c.isalnum() or c in ('_','-')).rstrip()
        base_filename = f"{doc_date}_{safe_sender}_{safe_doctype}"
        new_filename = f"{base_filename}.pdf"

        # --- NEW: Filename Collision Check ---
        final_path = os.path.join(PROCESSED_FOLDER, new_filename)
        counter = 1
        while os.path.exists(final_path):
            logging.warning(f"File '{final_path}' already exists. Appending a counter.")
            new_filename = f"{base_filename}-{counter}.pdf"
            final_path = os.path.join(PROCESSED_FOLDER, new_filename)
            counter += 1
        # --- END NEW ---
            
        logging.info(f"Moving file to: {final_path}")
        shutil.move(working_path, final_path)
        logging.info(f"--- Successfully processed {new_filename} ---")
        
        doc_date_str = analysis_data.get('doc_date')
        if doc_date_str:
            try:
                dt_object = datetime.strptime(doc_date_str, '%Y-%m-%d')
                timestamp = dt_object.timestamp()
                os.utime(final_path, (timestamp, timestamp))
                logging.info(f"Set file modification date for {new_filename} to {doc_date_str}")
            except (ValueError, TypeError) as e:
                logging.warning(f"Could not parse or set document date for {new_filename}: {e}")

    except Exception as e:
        logging.error(f"Failed to process {filename}: {e}", exc_info=True)
        if os.path.exists(working_path):
            error_path = os.path.join(ERROR_FOLDER, filename)
            logging.info(f"Moving failed file to: {error_path}")
            shutil.move(working_path, error_path)

def extract_text_with_pdftotext(pdf_path):
    # This function is now simplified, we just want the text.
    try:
        logging.info("Attempting to extract text with local pdftotext...")
        command = ['pdftotext', '-layout', pdf_path, '-']
        text = subprocess.check_output(command, text=True, encoding='utf-8')
        if text and len(text.strip()) > 20:
            logging.info("Successfully extracted text locally.")
            return text
        return None
    except Exception as e:
        logging.warning(f"pdftotext failed, likely an image-only PDF. Error: {e}")
        return None

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            time.sleep(2) 
            process_pdf(event.src_path)

if __name__ == "__main__":
    logging.info(f"Starting document processor with language setting: {OUTPUT_LANGUAGE}")
    for folder in [INBOX_FOLDER, PROCESSED_FOLDER, ERROR_FOLDER, WORKING_DIR]:
        if not os.path.isdir(folder):
            logging.info(f"Creating directory: {folder}")
            os.makedirs(folder)
    observer = Observer()
    event_handler = PDFHandler()
    observer.schedule(event_handler, INBOX_FOLDER, recursive=False)
    logging.info(f"Watching folder: {INBOX_FOLDER}")
    logging.info("Hybrid (Gemini + OCRmyPDF) script is running. Press Ctrl+C to stop.")
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: observer.stop()
    observer.join()
    logging.info("Script stopped.")
