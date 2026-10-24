
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

    text = text.lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def name_appears_in_text(name, ocr_text):
    """Compare entered name words with OCR words."""
    normalized_name = normalize_text(name)
    normalized_text = normalize_text(ocr_text)

    if not normalized_name or not normalized_text:
        return False

    name_words = normalized_name.split()
    ocr_words = normalized_text.split()

    for name_word in name_words:
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
                "Please upload or capture an image of your valid ID."
            )

        allowed_types = {"image/jpeg", "image/png"}

        if file.content_type not in allowed_types:
            raise forms.ValidationError(
                "Upload a JPG or PNG image only."
            )

        # Maximum upload size: 5 MB.
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "File size must not exceed 5 MB."
            )

        try:
            # Check that the file is a valid image.
            file.seek(0)
            with Image.open(file) as original:
                original.verify()

            # Reopen and prepare a smaller image.
            file.seek(0)
            with Image.open(file) as original:
                image = ImageOps.exif_transpose(original)
                image = ImageOps.grayscale(image)

                # Limit image dimensions to reduce memory use.
                image.thumbnail(
                    (1600, 1600),
                    Image.Resampling.LANCZOS,
                )

                image = ImageEnhance.Contrast(image).enhance(1.5)

                # Run OCR once, with an 8-second timeout.
                try:
                    ocr_text = pytesseract.image_to_string(
                        image,
                        lang="eng",
                        config="--oem 3 --psm 6",
                        timeout=8,
                    )
                except RuntimeError:
                    raise forms.ValidationError(
                        "ID verification took too long. "
                        "Please try a smaller, clearer JPG or PNG image."
                    )

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

        # Require readable text from the ID.
        if len(normalize_text(ocr_text)) < 3:
            raise forms.ValidationError(
                "No readable text was found. "
                "Please take a clearer photo of your Student ID."
            )

        first_name = self.cleaned_data.get("first_name", "")
        last_name = self.cleaned_data.get("last_name", "")

        first_matches = name_appears_in_text(
            first_name, ocr_text
        )
        last_matches = name_appears_in_text(
            last_name, ocr_text
        )

        if not first_matches or not last_matches:
            raise forms.ValidationError(
                "The name you entered does not match the name "
                "read from your ID. Please check your name and "
                "try a clear, well-lit photo of your Student ID."
            )

        file.seek(0)
        return file
