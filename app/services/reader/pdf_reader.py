import fitz  # PyMuPDF

from .base_reader import BaseReader


class PdfReader(BaseReader):
    async def read(self, file_bytes: bytes) -> str:
        text = ""
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
        return text
