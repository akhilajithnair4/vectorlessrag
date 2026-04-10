"""""
parsers/ folder = READ different file formats
Convert any file → plain text
So the rest of framework only works with text
"""

from dataclasses import dataclass
from typing import Optional
import pdfplumber
import fitz
from llms.base import BaseLLM
from prompts.parser_prompt  import PARSER_PROMPT


@dataclass
class Document:
    text: str #raw text of the document
    pages: list = None  
    total_pages: Optional[int] = None 
    total_characters: Optional[int] = None

class PDFParser:
    def __init__(self, file_path: str,mode:str,llm=None):
        self.file_path = file_path
        self.mode = mode
        self.llm = llm
    
    def parse(self) -> Document:
        try:
            if self.mode == "text":
                with pdfplumber.open(self.file_path) as pdf:
                    text = ""
                    pages = []
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        pages.append(page_text)
                        text += page_text + "\n"
                    total_pages = len(pdf.pages)
                    total_characters = len(text)
                    return Document(text=text, pages=pages,total_pages=total_pages, total_characters=total_characters)
                
            elif self.mode == "vision":
                doc = fitz.open(self.file_path)
                pages = []
                for page in doc:
                    image_bytes = page.get_pixmap(dpi=150).tobytes("png")  # parser converts page → image
                    text = self.llm.call_vision(PARSER_PROMPT, image_bytes)  # LLM reads image
                    pages.append(text)  
                full_text = "\n\n".join(pages)
                return Document(text=full_text, pages=pages, total_pages=len(pages), total_characters=len(full_text))

        except Exception as e:
            print(f"Error parsing PDF: {e}")
            return Document(text="")
        
if __name__ == "__main__":
    parser = PDFParser(file_path="sample.pdf",mode="text")
    document = parser.parse()
    
    print(document.text)
    