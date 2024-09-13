import os
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import boto3

# Configure Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# AWS Translate configuration
translate = boto3.client(
    'translate',
    aws_access_key_id='',
    aws_secret_access_key='',
    region_name='us-east-1'  # Change this to your AWS region
)

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using OCR."""
    images = convert_from_path(pdf_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img, lang='eng+guj+hin')
    return text

def translate_text(text, source_lang, target_lang='en'):
    """Translate text using AWS Translate with chunking."""
    # AWS Translate has a 5000-byte limit,so we are chunking it 
    chunk_size = 3000 

    translated_text = ""
    text_length = len(text)
    start_index = 0

    while start_index < text_length:
        end_index = min(start_index + chunk_size, text_length)
        chunk = text[start_index:end_index]

        response = translate.translate_text(
            Text=chunk,
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang
        )
        translated_text += response['TranslatedText']
        start_index = end_index

    return translated_text

def process_pdfs_in_folder(folder_path):
    """Process all PDF files in the given folder."""
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(folder_path, filename)
            print(f"Processing file: {filename}")

            # Extract text
            extracted_text = extract_text_from_pdf(pdf_path)
            
            # Determine source language for translation
            if 'guj' in extracted_text:
                source_lang = 'gu'
            elif 'hin' in extracted_text:
                source_lang = 'hi'
            else:
                source_lang = 'auto'

            # Translate text
            translated_text = translate_text(extracted_text, source_lang)

            # Save the translated text to a file
            base_filename = os.path.splitext(filename)[0]
            output_filename = f"{base_filename}_eng.txt"
            with open(os.path.join(folder_path, output_filename), 'w', encoding='utf-8') as f:
                f.write(translated_text)

            print(f"Translated file saved as: {output_filename}")

# Folder path containing PDF files
folder_path = 'Document_Folder'

# Process the PDFs in the specified folder
process_pdfs_in_folder(folder_path)
