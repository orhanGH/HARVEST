# OCR model options

## 1. Tesseract

Cheap baseline. Produces text and word boxes. Weak table structure.

Folder:
ocr_models/tesseract/

## 2. PaddleOCR / PP-StructureV3

Best first free candidate for table structure.

Expected output:
Markdown / JSON / structured document output.

Why:
PP-StructureV3 is intended for document image parsing and structured JSON/Markdown output.

Folder:
ocr_models/paddle/

## 3. Chandra OCR

Local OCR model producing structured Markdown/HTML/JSON.

Good candidate if GPU memory is enough.

Folder:
ocr_models/chandra/

## 4. Surya

OCR + layout + reading order + table recognition.

Potential issue:
new Surya backend may require vLLM on NVIDIA GPU or llama.cpp CPU backend.

Folder:
ocr_models/surya/
