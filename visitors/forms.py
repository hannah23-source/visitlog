
import os
import re
import shutil
import unicodedata
from difflib import SequenceMatcher

from django import forms
from PIL import (
    Image,
    ImageOps,
    ImageEnhance,
    UnidentifiedImageError,
)
import pytesseract

from .models import Visitor


# Find Tesseract automatically on Windows or Render/Linux.
tesseract_path = shutil.which("tesseract")

if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
elif os.name == "nt":
    windows_tesseract_path = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )
    if os.path.isfile(windows_tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = (
            windows_tesseract_path
        )


def normalize_text(text):
    """Normalize text for name comparison."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def name_appears_in_text(name, ocr_text):
    """Check whether a name appears in OCR text."""
    normalized_name = normalize_text(name)
    normalized_text = normalize_text(ocr_text)

    if not normalized_name or not normalized_text:
        return False

    name_words = normalized_name.split()
    ocr_words = normalized_text.split()

    for name_word in name_words:
        # Exact matches are preferred; allow minor OCR mistakes.
        if name_word in ocr_words:
            continue

        best_similarity = max(
            (
                SequenceMatcher(
                    None, name_word, ocr_word
                ).ratio()
                for ocr_word in ocr_words
            ),
            default=0,
        )

        if best_similarity < 0.84:
            return False

    return True


class VisitorForm(forms.ModelForm):

    class Meta:
        model = Visitor
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "contact_number",
            "purpose",
            "id_document",
        ]

    def clean_id_document(self):
        file = self.cleaned_data.get("id_document")

        if not file:
            raise forms.ValidationError(
                "Please upload or capture a photo of your valid ID."
            )

        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "File size must not exceed 5 MB."
            )

        allowed_types = {"image/jpeg", "image/png"}
        if file.content_type not in allowed_types:
            raise forms.ValidationError(
                "Upload a JPG or PNG image of your ID only."
            )

        try:
            file.seek(0)

            # Verify the image's actual format, not only its filename.
            with Image.open(file) as original:
                if original.format not in {"JPEG", "PNG"}:
                    raise forms.ValidationError(
                        "Please upload a valid JPG or PNG ID image."
                    )
                original.verify()

            file.seek(0)

            with Image.open(file) as original:
                # Correct phone-camera rotation before OCR.
                image = ImageOps.exif_transpose(original)

                # Resize BEFORE grayscale and contrast processing.
                # This reduces memory usage on the Render server.
                image.thumbnail(
                    (1200, 1200),
                    Image.Resampling.LANCZOS,
                )

                image = image.convert("L")
                image = ImageEnhance.Contrast(image).enhance(1.4)

                # Run OCR only once to reduce processing time.
                try:
                    ocr_text = pytesseract.image_to_string(
                        image,
                        lang="eng",
                        config="--oem 3 --psm 6",
                        timeout=12,
                    )
                except RuntimeError:
                    raise forms.ValidationError(
                        "ID verification took too long. "
                        "Please use a clear, well-lit photo of your ID."
                    )

        except forms.ValidationError:
            raise

        except pytesseract.TesseractNotFoundError:
            raise forms.ValidationError(
                "ID verification is temporarily unavailable. "
                "Please contact school staff."
            )

        except pytesseract.TesseractError:
            raise forms.ValidationError(
                "Could not read the ID image. "
                "Please try a clearer photo."
            )

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
        ):
            raise forms.ValidationError(
                "The image could not be opened. "
                "Please upload a valid JPG or PNG."
            )

        finally:
            file.seek(0)

        # Require enough readable text to attempt name matching.
        normalized_ocr = normalize_text(ocr_text)

        if len(normalized_ocr) < 3:
            raise forms.ValidationError(
                "No readable text was found. "
                "Please take a clear photo of your ID."
            )

        first_name = self.cleaned_data.get("first_name", "")
        last_name = self.cleaned_data.get("last_name", "")

        if not name_appears_in_text(first_name, ocr_text):
            raise forms.ValidationError(
                "Your first name does not match the name read "
                "from your ID. Please check your entry and photo."
            )

        if not name_appears_in_text(last_name, ocr_text):
            raise forms.ValidationError(
                "Your surname does not match the name read "
                "from your ID. Please check your entry and photo."
            )

        file.seek(0)
        return file
