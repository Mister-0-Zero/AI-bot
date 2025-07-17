from io import BytesIO

import pandas as pd

from .base_reader import BaseReader


class ExcelReader(BaseReader):
    async def read(self, file_bytes: bytes) -> str:
        """
        Читает Excel-файл, собирая ВСЕ листы.
        Каждый лист помечается заголовком === Лист: <имя> ===,
        а данные выводятся в CSV-формате (с заголовками колонок).
        """
        # sheet_name=None => получаем словарь {имя_листа: DataFrame}
        sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None, nrows=1000)

        parts: list[str] = []
        for sheet_name, df in sheets.items():
            parts.append(f"=== Лист: {sheet_name} ===")
            parts.append(df.to_csv(index=False))  # сохраняем заголовки колонок

        return "\n".join(parts)
