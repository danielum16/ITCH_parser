import io
import os
import sys
import tempfile

# ensure src/ on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from pse_itch_parser import BinaryRecordParser, FieldSpec


def make_record(rec_type: bytes, symbol: bytes, price: int, record_length: int) -> bytes:
    # simple layout for test: 0:1 rec_type, 1-4 reserved, 4-10 symbol (ascii), 12-16 price uint_be
    b = bytearray(b"\x00" * record_length)
    b[0:1] = rec_type
    b[4:4+len(symbol)] = symbol
    b[12:16] = price.to_bytes(4, "big")
    return bytes(b)


def test_parser_basic():
    rl = 32
    r1 = make_record(b"A", b"ABC123", 1000, rl)
    r2 = make_record(b"B", b"XYZ987", 2500, rl)

    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.write(r1 + r2)
        tmp.flush()
        tmp.close()

        schema = [
            FieldSpec("rec_type", 0, 1, "ascii"),
            FieldSpec("symbol", 4, 6, "ascii"),
            FieldSpec("price", 12, 4, "uint_be"),
        ]

        with open(tmp.name, "rb") as f:
            p = BinaryRecordParser(f, record_length=rl, schema=schema)
            out = list(p)

        assert len(out) == 2
        assert out[0]["rec_type"] == "A"
        assert out[0]["symbol"] == "ABC123"
        assert out[0]["price"] == 1000
        assert out[1]["rec_type"] == "B"
        assert out[1]["symbol"] == "XYZ987"
        assert out[1]["price"] == 2500
    finally:
        os.unlink(tmp.name)
