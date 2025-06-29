from .base_reader import BaseReader

class TxtReader(BaseReader):
    async def read(self, file_bytes: bytes) -> str:
        return file_bytes.decode("utf-8", errors="ignore")