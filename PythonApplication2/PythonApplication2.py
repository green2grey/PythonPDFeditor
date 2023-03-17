import os
from pdfrw import PdfReader, PdfWriter
from pdfminer.high_level import extract_text
from io import BytesIO, StringIO
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import fitz
import re

def analyze_pdf(input_pdf):
    doc = fitz.open(input_pdf)
    sections = []
    image_data = []

    for page_number, page in enumerate(doc):
        blocks = page.get_text("blocks")
        for block in blocks:
            block_text = block[4]
            for match in re.finditer(r"{([^}]*)}", block_text):
                section = match.group(1)
                if section not in sections:
                    sections.append(section)

        image_list = page.get_images(full=True)
        for img in image_list:
            image_data.append((page_number, img))

    doc.close()
    return sections, image_data

def replace_images(doc, image_data):
    for i, (page_number, img) in enumerate(image_data):
        print(f"Image {i + 1}: Page {page_number + 1}")
        replace = input("Do you want to replace this image? (y/n): ").lower()
        if replace == 'y':
            image_path = input(f"Enter the path to the new image for image {i + 1}: ")
            page = doc[page_number]
            xref = img[0]
            base_image = doc.extract_image(xref)
            if base_image:
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                img_name = f"temp_image_{i}.{image_ext}"
                with open(img_name, "wb") as img_file:
                    img_file.write(image_bytes)
                search_results = page.search_for(img_name, hit_max=1)
                if search_results:
                    img_rect = search_results[0]
                    img_width, img_height = img[2:4]  # Extract image width and height
                    img_size = (img_width, img_height)
                    new_img = Image.open(image_path)
                    new_img = new_img.resize(img_size)  # Resize new image to match original image
                    new_img_name = f"temp_image_{i}_new.{image_ext}"
                    new_img.save(new_img_name)
                    page.insert_image(img_rect, filename=new_img_name)
                    os.remove(img_name)
                    os.remove(new_img_name)
                else:
                    print(f"Warning: Could not find image {i+1} on page {page_number+1}")
            else:
                print(f"Warning: Could not extract image {i+1} from input PDF")
                    
    return doc





def draw_image(c, image_path, x, y, width, height):
    try:
        img = Image.open(image_path)
        img_width, img_height = img.size

        aspect_ratio = img_height / img_width
        new_height = aspect_ratio * width

        if new_height > height:
            new_height = height
            new_width = img_width / img_height * new_height
        else:
            new_width = width

        c.drawImage(image_path, x, y, width=new_width, height=new_height)
    except FileNotFoundError:
        print(f"Error: Image file not found: {image_path}")

def customize_pdf(input_pdf, output_pdf, user_data, sections):
    doc = fitz.open(input_pdf)
    output_doc = fitz.open()

    for i, page in enumerate(doc):
        output_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)

        # Add images from input PDF to output PDF
        image_list = page.get_images(full=True)
        for img in image_list:
            xref = img[0]
            base_image = doc.extract_image(xref)
            if base_image:
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                img_rect = fitz.Rect(*img[1:5])
                if img_rect.width > 0 and img_rect.height > 0 and not any(map(math.isnan, img_rect)):
                    img_name = f"temp_image_{i}.{image_ext}"
                    with open(img_name, "wb") as img_file:
                        img_file.write(image_bytes)
                    output_page.insert_image(img_rect, filename=img_name)
                    os.remove(img_name)
                else:
                    print(f"Warning: Skipping image {i+1} on page {page.number + 1} due to invalid dimensions: {img_rect}")

        # Customize text
        blocks = page.get_text("blocks")
        for block in blocks:
            x, y, x1, y1 = block[:4]
            block_text = block[4]

            for section in sections:
                if user_data.get(section):
                    block_text = block_text.replace(f"{{{section}}}", user_data[section])

            output_page.insert_textbox((x, y, x1, y1), block_text, fontsize=12)

    output_doc.save(output_pdf)
    output_doc.close()
    doc.close()

def get_user_data(sections):
    user_data = {}

    for section in sections:
        value = input(f"Enter the value for {section}: ")
        user_data[section] = value

    return user_data

def main():
    input_pdf = input("Enter the path to the input PDF: ")
    output_pdf = input("Enter the path to the output PDF: ")

    sections, image_data = analyze_pdf(input_pdf)
    user_data = get_user_data(sections)

    doc = fitz.open(input_pdf)
    doc = replace_images(doc, image_data)
    customize_pdf(doc, output_pdf, user_data, sections)
    doc.close()

if __name__ == "__main__":
    main()