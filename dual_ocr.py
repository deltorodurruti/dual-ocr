import argparse
import difflib
import importlib.util
import io
import os
import re
import statistics
import sys

ENGINE_MODES = ("dual", "tesseract", "rapid")
DICTIONARY_PATHS = ("/usr/share/dict/words", "/usr/share/dict/web2")
SUFFIX_RULES = (("ies", "y"), ("es", ""), ("s", ""), ("ed", ""), ("d", ""), ("ing", ""), ("ly", ""))
SYMBOL_PATTERN = re.compile(r"[^\w\s.,;:!?'\"()\-–—’“”&%$@/]")

_rapid_engine = None
_dictionary = None


def engine_mode():
    mode = os.environ.get("DUAL_OCR_ENGINE", "dual").strip().lower()
    return mode if mode in ENGINE_MODES else "dual"


def bundled_tesseract():
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return
    tessdir = os.path.join(base, "Tesseract-OCR")
    exe = os.path.join(tessdir, "tesseract.exe")
    if os.path.exists(exe):
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = exe
            os.environ.setdefault("TESSDATA_PREFIX", os.path.join(tessdir, "tessdata"))
        except Exception:
            pass


bundled_tesseract()


def load_dictionary():
    global _dictionary
    if _dictionary is None:
        _dictionary = set()
        for path in DICTIONARY_PATHS:
            try:
                with open(path, encoding="utf-8", errors="ignore") as handle:
                    _dictionary = {line.strip().lower() for line in handle if line.strip()}
                break
            except OSError:
                continue
    return _dictionary


def normalize(word):
    return re.sub(r"[^A-Za-z0-9]", "", word).lower()


def is_valid_word(word):
    key = normalize(word)
    if not key:
        return False
    if key.isdigit() or len(key) == 1:
        return True
    dictionary = load_dictionary()
    if not dictionary:
        return bool(re.search(r"[aeiouy]", key))
    candidates = [key]
    for suffix, replacement in SUFFIX_RULES:
        if key.endswith(suffix) and len(key) > len(suffix) + 2:
            candidates.append(key[: -len(suffix)] + replacement)
    return any(candidate in dictionary for candidate in candidates)


def is_acceptable_alone(word):
    return is_valid_word(word) or (word[:1].isupper() and bool(normalize(word)))


def count_symbols(block):
    return sum(len(SYMBOL_PATTERN.findall(word)) for word, _ in block)


def tokens_from_paragraphs(paragraphs):
    tokens = []
    for paragraph in paragraphs:
        for index, word in enumerate(paragraph.split()):
            tokens.append((word, index == 0))
    return tokens


def paragraphs_from_tokens(tokens):
    paragraphs, current = [], []
    for word, starts in tokens:
        if starts and current:
            paragraphs.append(" ".join(current))
            current = []
        current.append(word)
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def fuse(reading_a, reading_b):
    keys_a = [normalize(word) for word, _ in reading_a]
    keys_b = [normalize(word) for word, _ in reading_b]
    matcher = difflib.SequenceMatcher(None, keys_a, keys_b, autojunk=False)
    merged = []
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(a2 - a1):
                word, starts_a = reading_a[a1 + offset]
                starts_b = reading_b[b1 + offset][1]
                merged.append((word, starts_a or starts_b))
        elif tag == "replace":
            block_a = reading_a[a1:a2]
            block_b = reading_b[b1:b2]
            score_a = (sum(is_valid_word(word) for word, _ in block_a), -count_symbols(block_a))
            score_b = (sum(is_valid_word(word) for word, _ in block_b), -count_symbols(block_b))
            a_wins = score_a >= score_b
            winner, loser = (block_a, block_b) if a_wins else (block_b, block_a)
            loser_starts = bool(loser) and loser[0][1]
            for offset, (word, starts) in enumerate(winner):
                if is_acceptable_alone(word):
                    merged.append((word, starts or (loser_starts and offset == 0)))
        elif tag == "delete":
            merged.extend((word, starts) for word, starts in reading_a[a1:a2] if is_acceptable_alone(word))
        elif tag == "insert":
            merged.extend((word, starts) for word, starts in reading_b[b1:b2] if is_acceptable_alone(word))
    return paragraphs_from_tokens(merged)


def fill_color(image):
    return 255 if image.mode in ("L", "1") else (255, 255, 255)


def binarize(image):
    try:
        import cv2
        import numpy as np
        from PIL import Image
        gray = np.asarray(image.convert("L"))
        gray = cv2.medianBlur(gray, 3)
        gray = cv2.fastNlMeansDenoising(gray, h=10)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binary = cv2.copyMakeBorder(binary, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
        return Image.fromarray(binary)
    except Exception:
        return image


def orient(image):
    try:
        import pytesseract
        osd = pytesseract.image_to_osd(image)
        degrees = int(re.search(r"Rotate:\s*(\d+)", osd).group(1))
    except Exception:
        return image
    if degrees in (90, 180, 270):
        return image.rotate(-degrees, expand=True, fillcolor=fill_color(image))
    return image


def deskew(image):
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return image
    gray = image.convert("L")
    scale = 800.0 / max(gray.size)
    small = gray.resize((max(1, int(gray.width * scale)), max(1, int(gray.height * scale)))) \
        if scale < 1 else gray
    angles = [0.0]
    for step in range(1, 11):
        angles += [step * 0.5, -step * 0.5]
    best_angle, best_score = 0.0, -1.0
    for angle in angles:
        rotated = small.rotate(angle, resample=Image.BILINEAR, fillcolor=255)
        ink = 255.0 - np.asarray(rotated, dtype=np.float32)
        profile = ink.sum(axis=1)
        score = float(((profile[1:] - profile[:-1]) ** 2).sum())
        if score > best_score:
            best_score, best_angle = score, angle
    if abs(best_angle) < 0.3:
        return image
    return image.rotate(best_angle, resample=Image.BICUBIC, fillcolor=fill_color(image), expand=True)


def prepare(image, preprocess, straighten, use_orientation):
    from PIL import ImageOps
    if use_orientation and straighten:
        image = orient(image)
    if preprocess:
        try:
            image = ImageOps.autocontrast(ImageOps.grayscale(image))
        except Exception:
            pass
    if straighten:
        try:
            image = deskew(image)
        except Exception:
            pass
    if preprocess:
        image = binarize(image)
    return image


def split_paragraphs(text):
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        joined = " ".join(line.strip() for line in block.splitlines() if line.strip()).strip()
        if joined:
            paragraphs.append(joined)
    return paragraphs


def rapid_lines_to_text(result):
    if result.boxes is None or not len(result.txts):
        return ""
    lines = []
    for box, text in zip(result.boxes, result.txts):
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        lines.append((min(ys), min(xs), max(xs), text))
    lines.sort(key=lambda line: line[0])
    gaps = [later[0] - earlier[0] for earlier, later in zip(lines, lines[1:]) if later[0] - earlier[0] > 0]
    step = statistics.median(gaps) if gaps else 0
    margin = statistics.median(line[1] for line in lines)
    width = max(line[2] for line in lines)
    pieces = [lines[0][3]]
    for previous, current in zip(lines, lines[1:]):
        new_paragraph = (current[0] - previous[0] > 1.3 * step) or (current[1] - margin > 0.03 * width)
        pieces.append(("\n\n" if new_paragraph else "\n") + current[3])
    return "".join(pieces)


def get_rapid_engine():
    global _rapid_engine
    if _rapid_engine is None:
        from rapidocr import LangRec, RapidOCR
        _rapid_engine = RapidOCR(params={"Rec.lang_type": LangRec.EN})
    return _rapid_engine


def read_tesseract(image, lang="eng", psm=3, oem=1):
    import pytesseract
    text = pytesseract.image_to_string(image, lang=lang, config=f"--oem {oem} --psm {psm}")
    return split_paragraphs(text)


def read_rapid(image):
    import numpy as np
    result = get_rapid_engine()(np.array(image.convert("RGB")))
    return split_paragraphs(rapid_lines_to_text(result))


def tesseract_available():
    if importlib.util.find_spec("pytesseract") is None:
        return False
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


def rapid_available():
    return importlib.util.find_spec("rapidocr") is not None


def read_page(png_bytes, lang="eng", psm=3, oem=1, preprocess=True, straighten=True, mode=None):
    from PIL import Image
    mode = mode or engine_mode()
    image = Image.open(io.BytesIO(png_bytes))
    readings = []
    if mode in ("dual", "tesseract") and tesseract_available():
        try:
            base = prepare(image, preprocess, straighten, use_orientation=True)
            readings.append(tokens_from_paragraphs(read_tesseract(base, lang, psm, oem)))
        except Exception:
            pass
    if mode in ("dual", "rapid") and rapid_available():
        try:
            base = prepare(image, preprocess, straighten, use_orientation=False)
            readings.append(tokens_from_paragraphs(read_rapid(base)))
        except Exception:
            pass
    if not readings:
        raise RuntimeError("no OCR engine available: install pytesseract or rapidocr")
    if len(readings) == 2:
        return fuse(readings[0], readings[1])
    return paragraphs_from_tokens(readings[0])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read a scanned page with Tesseract and RapidOCR and fuse both readings.")
    parser.add_argument("image", help="PNG or JPEG page image")
    parser.add_argument("--engine", choices=ENGINE_MODES, default=None,
                        help="dual (default), tesseract or rapid")
    parser.add_argument("--lang", default="eng", help="Tesseract language code")
    arguments = parser.parse_args(argv)
    with open(arguments.image, "rb") as handle:
        paragraphs = read_page(handle.read(), lang=arguments.lang, mode=arguments.engine)
    for paragraph in paragraphs:
        print(paragraph)
        print()


if __name__ == "__main__":
    main()
