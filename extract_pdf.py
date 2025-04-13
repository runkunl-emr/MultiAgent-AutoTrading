import PyPDF2

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text() + "\n\n"
        return text

if __name__ == "__main__":
    pdf_path = "Quant-design-doc.pdf"
    extracted_text = extract_text_from_pdf(pdf_path)
    
    # Write the extracted text to a file
    with open("Quant-design-doc.txt", "w", encoding="utf-8") as text_file:
        text_file.write(extracted_text)
        
    print("Text has been extracted and saved to Quant-design-doc.txt") 