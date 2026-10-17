# dual-ocr

Reads a scanned page with two OCR engines, Tesseract and RapidOCR, and merges both readings word by word so you keep the cleaner text.

## What it is for

It pulls text out of scanned or photographed pages, especially old books with uneven typography. It returns the text already split into paragraphs, ready to read, translate or search.

## Why it exists

No OCR engine is right every time. In our tests on a scanned book we saw this:

- Tesseract separates paragraphs well and reads the body text well, but it sometimes confuses similar letters and it falls apart on pages with decorative type.
- RapidOCR gets letters right more often, but sometimes it merges text that should be split into separate paragraphs.

When one engine fails, the other usually gets it right, and they rarely fail on the same words. So the project reads each page with both and compares. Where the readings agree, it keeps the word and the paragraph breaks marked by either engine. Where they differ, it keeps the reading with more valid English words: if one reads "LNountains" and the other "mountains", it keeps "mountains".

This does not replace a human check. The tie-breaker is a dictionary, so it can still be wrong when both engines fail the same way, with proper names the dictionary does not contain, or with symbols that look like words. If you publish or translate the output, read the pages with odd text.

## How it works

1. The image is prepared: grayscale, autocontrast, fine deskew and binarization with OpenCV.
2. Tesseract reads the page. Its orientation check (90 or 180 degrees) runs first.
3. RapidOCR reads the same page without that correction, because its model already classifies orientation.
4. The two readings are aligned word by word with `difflib` from the standard library and merged with the rules above.

If one engine is not installed, the project uses only the other. If neither is installed, it raises a clear error.

## Installation

You need Python (tested with 3.11) and the Tesseract program on your system:

- macOS: `brew install tesseract`
- Debian or Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-eng`
- Windows: the UB Mannheim installer

Then, from the project directory:

```
pip install -r requirements.txt
```

## Usage

From the command line, with a page image:

```
python dual_ocr.py page.png
python dual_ocr.py page.png --engine tesseract
python dual_ocr.py page.png --engine rapid
```

From Python:

```python
from dual_ocr import read_page

with open("page.png", "rb") as handle:
    paragraphs = read_page(handle.read())

for paragraph in paragraphs:
    print(paragraph)
```

You can also set the mode with the `DUAL_OCR_ENGINE` environment variable (`dual`, `tesseract` or `rapid`). The default is `dual`.

For a scanned PDF, first convert each page to an image. For example, with PyMuPDF: `page.get_pixmap(dpi=300).tobytes("png")`. 300 dpi is a good starting point.

## Tests

```
python -m unittest discover -s tests -v
```

The tests cover merging readings, dropping stray symbols, word validation, and paragraph detection from indentation and vertical gaps. They do not test the OCR engines themselves.

## Limitations

- Errors that both engines share are not corrected.
- Proper names missing from the dictionary are kept as the engine reads them, and they cannot be corrected with certainty.
- The dictionary comes from `/usr/share/dict/words` (macOS and Linux). Windows has no such file, so the project falls back to a simpler rule that only checks for vowels. That is weaker.
- Pages with decorative lettering are hard for any engine.

## Credits

This project depends on the work of many people and communities. Thank you to all of them:

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract), which has been open work on text recognition for years. It started at HP, and Google and the community maintain it. Apache-2.0 license.
- [pytesseract](https://github.com/madmaze/pytesseract), the bridge that makes Tesseract usable from Python. Apache-2.0 license.
- [RapidOCR](https://github.com/RapidAI/RapidOCR), which runs the PP-OCR models on ONNX without requiring PaddlePaddle. Apache-2.0 license.
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) and the PaddlePaddle team at Baidu, authors of the PP-OCR models that RapidOCR uses. Apache-2.0 license.
- [ONNX Runtime](https://github.com/microsoft/onnxruntime), by Microsoft. MIT license.
- [OpenCV](https://github.com/opencv/opencv), for image preprocessing. Apache-2.0 license.
- [Pillow](https://github.com/python-pillow/Pillow) and [NumPy](https://github.com/numpy/numpy), the base for all image and array handling. Permissive licenses.

## License

MIT. See `LICENSE`.
