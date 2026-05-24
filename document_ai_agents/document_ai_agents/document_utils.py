import io
import fitz
from PIL import Image
from pypdf import PdfReader

from document_ai_agents.logger import logger


def extract_images_from_pdf(pdf_path: str):
    logger.info(f"Extracting images from PDF: {pdf_path}")
    images = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            pix = page.get_pixmap()
            img_data = pix.tobytes("jpeg")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
        logger.info(f"Extracted {len(images)} images from the PDF using PyMuPDF.")
    except Exception as e:
        logger.error(f"Failed to extract images using PyMuPDF: {e}")
    return images


def extract_text_from_pdf(pdf_path: str):
    logger.info(f"Extracting text from PDF: {pdf_path}")
    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        logger.info(f"Extracting text from {len(reader.pages)} pages.")
        texts = [page.extract_text() for page in reader.pages]
        logger.info(f"Extracted text from {len(texts)} pages.")
        return texts
