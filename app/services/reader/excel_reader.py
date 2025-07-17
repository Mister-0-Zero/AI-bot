from io import BytesIO

import pandas as pd

from .base import BaseReader


class ExcelReader(BaseReader):
    async def read(self, file_bytes: bytes) -> str:
        """
        Читает Excel-файл (берёт первый лист), возвращает текст в CSV-формате.
        """
        df = pd.read_excel(BytesIO(file_bytes), sheet_name=0, nrows=1000)
        return df.to_csv(index=False)
