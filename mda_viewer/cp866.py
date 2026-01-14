# cp866_table.py
from itertools import chain

# CP866: tuple из 256 элементов; каждый элемент — UTF-8 bytes для байта 0..255
CP866 = tuple(
    bytes([i]).decode("cp866", errors="strict").encode("utf-8")
    for i in range(256)
)

def cp866_to_utf8(data: bytes) -> str:
    # полностью аналогично твоему cp437_to_utf8
    return bytes(chain.from_iterable(CP866[b] for b in data)).decode("utf-8")

# (опционально) быстрый вариант без таблицы, если она не нужна:
def cp866_to_utf8_fast(data: bytes) -> str:
    return data.decode("cp866", errors="strict")