from flask import Flask, render_template, request, send_file
import os
from dotenv import load_dotenv
from openai import OpenAI
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import docx  # python-docx
from datetime import datetime

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

def extract_text_from_file(filepath):
    if filepath.endswith('.txt'):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    elif filepath.endswith('.docx'):
        doc = docx.Document(filepath)
        return '\n'.join([para.text for para in doc.paragraphs])
    elif filepath.endswith('.pdf'):
        text = ''
        with fitz.open(filepath) as pdf:
            for page in pdf:
                text += page.get_text()
        return text
    else:
        return ''

def save_translation_log(english_text, spanish, final_english):
    filename = datetime.now().strftime("translation_%Y%m%d_%H%M%S.txt")
    path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write("Original English:\n")
        f.write(english_text + "\n\n")
        f.write("Translated Spanish:\n")
        f.write(spanish + "\n\n")
        f.write("Final English (after editing):\n")
        f.write(final_english)
    return path

@app.route('/', methods=['GET', 'POST'])
def index():
    translated_spanish = ''
    edited_english = ''
    download_file = ''
    english_text = ''

    if request.method == 'POST':
        # Get direct input text
        english_text = request.form.get('english', '')

        # Process multiple file uploads
        uploaded_files = request.files.getlist('files')
        for file in uploaded_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                english_text += '\n' + extract_text_from_file(filepath)

        # Step 1: English → Spanish
        if english_text.strip():
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"Translate this to Spanish: {english_text}"}]
            )
            translated_spanish = response.choices[0].message.content

        # Step 2: Spanish → English
        elif 'spanish' in request.form and request.form['spanish']:
            spanish_text = request.form['spanish']
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"Translate this to English: {spanish_text}"}]
            )
            edited_english = response.choices[0].message.content

            # Save the translation log
            download_file = save_translation_log(request.form.get('original_english', ''), spanish_text, edited_english)

    return render_template('index.html',
                           translated_spanish=translated_spanish,
                           edited_english=edited_english,
                           download_file=download_file,
                           original_english=english_text)

@app.route('/download/<filename>')
def download(filename):
    path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
