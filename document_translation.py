import os
from PIL import Image
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_detection_model, load_processor as load_detection_processor
from surya.model.recognition.model import load_model as load_recognition_model
from surya.model.recognition.processor import load_processor as load_recognition_processor
from pdf2image import convert_from_path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import boto3

def process_pdf(pdf_path, langs=["en"], dpi=300):
    # Convert PDF pages to images with higher DPI
    images = convert_from_path(pdf_path, dpi=dpi)

    # Load OCR models and processors
    det_processor, det_model = load_detection_processor(), load_detection_model()
    rec_model, rec_processor = load_recognition_model(), load_recognition_processor()

    all_predictions = []

    # Run OCR on each page image
    for image in images:
        predictions = run_ocr([image], [langs], det_model, det_processor, rec_model, rec_processor)
        all_predictions.extend(predictions)

    return all_predictions

def translate_text(text, source_lang='hi', target_lang='en'):
    if not text.strip():  # Check if the text is empty or just whitespace
        return ""  # Return an empty string if there's no text to translate
    
    translate = boto3.client(
        'translate',
        aws_access_key_id='YOUR_AWS_ACCESS_KEY',
        aws_secret_access_key='YOUR_AWS_SECRET_KEY',
        region_name='us-east-1'
    )
    
    response = translate.translate_text(
        Text=text,
        SourceLanguageCode=source_lang,
        TargetLanguageCode=target_lang
    )
    
    return response['TranslatedText']

def translate_predictions(predictions):
    translated_predictions = []

    for ocr_result in predictions:  # predictions is a list of OCRResult objects
        for text_line in ocr_result.text_lines:  # Iterate over text_lines in each OCRResult
            translated_text = translate_text(text_line.text)
            translated_predictions.append({
                'original_text': text_line.text,
                'translated_text': translated_text,
                'confidence': text_line.confidence,
                'bbox': text_line.bbox
            })
    
    return translated_predictions

def create_translated_pdf(output_pdf_path, translated_predictions):
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    
    # A4 dimensions in points: 595 x 842 (width x height)
    page_width, page_height = A4

    # Determine the maximum possible x and y values from the bbox to calculate the scaling factor
    max_bbox_width = 2200  # Replace with the actual maximum x2 value in your dataset
    max_bbox_height = 800

    x_offset=-90
    y_offset=-400

    # Scale factor to map the bounding box coordinates to the PDF page size
    x_scale = page_width / max_bbox_width
    y_scale = page_height / max_bbox_height

    # Fixed line height (adjust this value as needed)
    line_height = 8  # Example line height in points

    # Starting y-position (from top of the page)
    current_y_position = page_height - 50  # Start 50 points down from the top

    # Minimum y-position before a new page is needed
    bottom_margin = 50  # 50 points margin from the bottom

    # Maximum width for the text before wrapping
    max_text_width = page_width - 40  # Leaving some margin on both sides

    for prediction in translated_predictions:
        # Extracting bounding box coordinates
        x1, y1, x2, y2 = prediction['bbox']

        # Scale the x coordinates
        scaled_x1 = x1 * x_scale + x_offset
        scaled_y1 = y1 * y_scale + y_offset
        scaled_x2 = x2 * x_scale + x_offset
        scaled_y2 = y2 * y_scale + y_offset

        # Calculate text position based on fixed y position
        text_x = scaled_x1
        text_y = current_y_position

        # Set font and size
        c.setFont("Helvetica", 8)

        # Split the text into lines that fit within max_text_width
        wrapped_lines = simpleSplit(prediction['translated_text'], c._fontname, c._fontsize, max_text_width)

        for line in wrapped_lines:
            if text_y < bottom_margin + line_height:
                # If y position is below bottom margin, start a new page
                c.showPage()
                current_y_position = page_height - 50
                text_y = current_y_position
                text_x = scaled_x1  # Reset text_x if necessary

            c.drawString(text_x, text_y, line)
            text_y -= line_height  # Move down to the next line

        # Move the current_y_position down for the next block of text
        current_y_position = text_y - line_height

    # Save the PDF
    c.save()


def process_pdfs_in_folders(input_folder, output_folder):
    for filename in os.listdir(input_folder):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(input_folder, filename)
            predictions = process_pdf(pdf_path)
            translated_predictions = translate_predictions(predictions)
            output_pdf_path = os.path.join(output_folder, filename.replace(".pdf", "_eng.pdf"))
            create_translated_pdf(output_pdf_path, translated_predictions)

# Example usage
input_folder = "Input folder"  # Replace with the path to the input folder containing your PDFs
output_folder = "output folder"  # Replace with the path to the output folder where translated PDFs will be saved
process_pdfs_in_folders(input_folder, output_folder)  