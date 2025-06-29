# **gemini-ocr-flow: Gemini-Powered Document Ingestion & Intelligence Pipeline**

## **Overview**

This project is a self-hosted, event-driven service that creates a fully automated processing pipeline for both scanned and born-digital PDF documents. It runs entirely in Docker on a home NAS (or any Linux-based server), managed by Docker Compose for resilience and automatic startup on boot.

The system intelligently uses a "smart OCR" workflow: it first attempts to extract text locally from text-based PDFs. If and only if the document is a scanned image, it falls back to using the Google Gemini Pro API for high-fidelity OCR. The extracted text is then sent back to Gemini for advanced analysis, including document type classification, sender identification, keyword generation, and date extraction. The final output is a searchable, archival-grade PDF/A file, perfectly named, tagged with rich metadata, and timestamped to match the document's content.

This was just a learning project for me, for a more complete solution see https://paperless-ngx.com/

## **Features**

* **Automated Ingestion:** Automatically processes any PDF file dropped into a designated inbox folder.  
* **Smart Text Detection:** Uses pdftotext to instantly extract text from digital PDFs, saving time and API costs.  
* **AI-Powered OCR:** Falls back to the Gemini Pro API for high-accuracy OCR on image-based scans.  
* **Configurable AI Analysis:** The intelligence layer is fully configurable via an .env file. You can specify the output language (english, french, or both) to dynamically change the analysis prompts.  
* **Intelligent Renaming:** Automatically renames files into a clean, consistent YYYY-MM-DD\_Sender\_DocType.pdf format based on AI analysis.  
* **Filesystem Timestamping:** Corrects the file's "Date Modified" to match the actual date found within the document's content.  
* **Atomic** PDF/A Creation & Metadata **Injection:** Uses ocrmypdf to create a searchable, archival-grade PDF/A file and injects all metadata (Title, Author/Sender, Subject, Keywords) in a single, reliable operation.  
* **Filename Collision Avoidance:** Automatically appends a counter (-1, \-2, etc.) if a file with the same generated name already exists, preventing any data loss.  
* **Resilient & Self-Healing:** Runs as a Docker service that automatically restarts on system boot or if it encounters an unexpected crash.  
* **Error Handling:** Moves any files that fail during processing to a dedicated error folder for manual inspection.

## **Technology Stack**

* **Orchestration:** Docker, Docker Compose  
* **Language:** Python 3  
* **Core AI:** Google Gemini Pro API  
* **Local Text Extraction:** pdftotext (from poppler-utils)  
* **PDF Creation & Metadata:** ocrmypdf  
* **Filesystem Watcher:** watchdog (in polling mode for NAS reliability)

## **Installation Guide**

### **Step 1: Prerequisites**

Before you begin, ensure the following are installed and configured on your host system (e.g., Asustor NAS, Synology, or any Linux server):

1. **Docker & Docker Compose:** Install from your system's App Center or package manager.  
2. **Git:** Install git from your system's package manager (sudo apt-get install git).  
3. **SSH Access:** Ensure you can connect to your server's command line via SSH for running the final commands.  
4. **User Permissions:** Your SSH user must have permission to run Docker commands. The easiest way is to add your user to the docker group:  
~~~
sudo usermod \-aG docker your\_username
~~~
   \# You MUST log out and log back in for this change to take effect.

5. **Gemini API Key:**  
   * Go to [Google AI Studio](https://aistudio.google.com/).  
   * Sign in and click **"Get API key"** to create a new key. Copy it securely.

### **Step 2: Create Parent Folder**

On your NAS or server, create a parent directory to hold the project files.
~~~
mkdir \-p /volume1/Docker/gemini-ocr-flow
~~~
### **Step 3: Download Project Files and Configure**

Connect to your server via SSH and navigate into the parent directory you just created.

1. Clone the Project from GitHub:  
   Run the following command to download all the project files.
   ~~~
   cd /volume1/Docker/gemini-ocr-flow/  
   git clone https://github.com/sblaisdev/gemini-ocr-flow.git .
   ~~~
   *(Note: The . at the end is important—it tells git to clone the files into the current folder, not a new subfolder.)*  
3. Create Your Configuration File:  
   The repository includes an example configuration file. Copy it to create your own local version, which will be safely ignored by Git.
   ~~~
   cp .env.example .env
   ~~~
5. Edit the Configuration File:  
   Open the newly created .env file with a text editor to add your personal API key.
   ~~~
   nano .env
   ~~~
   Edit the GEMINI\_API\_KEY variable and paste your secret API key from Google AI Studio.
   You can also change the OUTPUT\_LANGUAGE if desired.
   WARNING: When editing files on a Linux system, especially from a Windows machine, ensure your text editor is saving the file with UTF-8 encoding. Saving with a different encoding can cause the application to fail.  
7. Save and exit (Ctrl+X, Y, Enter).

### **Step 4: Launch the Service**

Now that everything is configured, you can build and run the service for the first time. The initial build may take several minutes as it downloads all the necessary software.

From the project's root directory (/volume1/Docker/gemini-ocr-flow/), run:
~~~
sudo docker-compose up \-d \--build
~~~
Your automated document processing service is now running\!

### **Usage**

* **To check the live logs:** sudo docker-compose logs \-f  
* **To stop the service:** sudo docker-compose down  
* **To start the service again (after it's been stopped):** sudo docker-compose up \-d  
* **To change the language:** Stop the service, edit the OUTPUT\_LANGUAGE variable in your .env file, and start the service again with sudo docker-compose up \-d. A rebuild is not necessary for this change.

## **License**

This project is licensed under the MIT License. See the LICENSE file for details.

## **Acknowledgements**

This project stands on the shoulders of giants. It would not be possible without the incredible work of the open-source community and the creators of the following tools:

* [**Gemini Pro**](https://gemini.google.com/) for helping create this project in all its steps from brainstorming, planning, coding, and debugging to providing the intelligence behind the scenes for OCR and document analysis.  
* [**OCRmyPDF**](https://github.com/ocrmypdf/OCRmyPDF) (MPL-2.0 License) for its robust and reliable PDF processing capabilities.  
* [**Poppler**](https://poppler.freedesktop.org/) (pdftotext utility \- GPL License) for its fast, local text extraction.  
* [**Python**](https://www.python.org/) and the rich ecosystem of libraries it provides.  
* [**Docker**](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) for making complex application deployment simple and repeatable.
