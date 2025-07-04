import io

from docx import Document

from .base_reader import BaseReader


class DocxReader(BaseReader):
    async def read(self, file_bytes: bytes) -> str:
        file_stream = io.BytesIO(file_bytes)
        doc = Document(file_stream)
        return "\n".join(p.text for p in doc.paragraphs if p.text)
