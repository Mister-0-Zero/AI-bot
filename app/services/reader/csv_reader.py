from io import BytesIO

import pandas as pd

from .base_reader import BaseReader


class CsvReader(BaseReader):
    async def read(self, file_bytes: bytes) -> str:
        """
        Читает CSV-файл из байтов, возвращает его как текст
        (разделитель автоматически определяется pandas).
        """
        df = pd.read_csv(BytesIO(file_bytes), nrows=2000)  # safety-лимит
        return df.to_csv(index=False)
