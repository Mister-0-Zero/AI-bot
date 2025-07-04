from abc import ABC, abstractmethod


class BaseReader(ABC):
    @abstractmethod
    async def read(self, file_bytes: bytes) -> str:
        """
        Асинхронно читает содержимое файла и возвращает его как текст.
        """
        pass
