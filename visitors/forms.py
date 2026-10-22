
import os
import re
import shutil
import unicodedata

from django import forms
from PIL import (
    Image,
    ImageOps,
    ImageEnhance,
    UnidentifiedImageError,
)
import pytesseract

from .models import Visitor


# Find Tesseract automatically on Render/Linux or Windows.
tesseract_path = shutil.which("tesseract")

if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
elif os.name == "nt":
    # Default Tesseract installation path on Windows.
    windows_tesseract_path = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    if os.path.isfile(windows_tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = (
            windows_tesseract_path
        )


def normalize_text(text):
    """Convert text to lowercase and remove punctuation."""
    text = unicodedata.normalize("NFKD", text)

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = text.lower()

    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def name_appears_in_text(name, ocr_text):
    """Check whether a complete name appears in OCR text."""
    normalized_name = normalize_text(name)
    normalized_text = normalize_text(ocr_text)

    if not normalized_name:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(normalized_name)
        + r"(?!\w)"
    )

    return re.search(pattern, normalized_text) is not None


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

        # Only JPG and PNG are supported for OCR.
        allowed_types = {
            "image/jpeg",
            "image/png",
        }

        if file.content_type not in allowed_types:
            raise forms.ValidationError(
                "Upload a JPG or PNG image only."
            )

        # Maximum file size: 5 MB.
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "File size must not exceed 5 MB."
            )

        try:
            # Verify that the uploaded file is a valid image.
            file.seek(0)

            with Image.open(file) as original:
                original.verify()

            # Reopen the image for OCR processing.
            file.seek(0)

            with Image.open(file) as original:
                image = ImageOps.exif_transpose(original)
                image = ImageOps.grayscale(image)
                image = ImageEnhance.Contrast(image).enhance(1.5)

                image = image.resize(
                    (
                        image.width * 2,
                        image.height * 2,
                    )
                )

                ocr_text = pytesseract.image_to_string(
                    image,
                    lang="eng",
                    config="--psm 6",
                )

        except pytesseract.TesseractNotFoundError:
            raise forms.ValidationError(
                "ID verification is temporarily unavailable because "
                "the OCR software is not installed or configured."
            )

        except pytesseract.TesseractError:
            raise forms.ValidationError(
                "Could not read the ID image. Please try a clearer photo."
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

        # Ensure OCR found some readable text.
        if not ocr_text or len(normalize_text(ocr_text)) < 3:
            raise forms.ValidationError(
                "No readable text was found. "
                "Please take a clearer photo of your ID."
            )

        # Compare the visitor's first and last names with the ID.
        first_name = self.cleaned_data.get("first_name", "")
        last_name = self.cleaned_data.get("last_name", "")
        middle_name = self.cleaned_data.get("middle_name", "")

        if not name_appears_in_text(first_name, ocr_text):
            raise forms.ValidationError(
                "The first name could not be found on the ID. "
                "Check your spelling or upload a clearer image."
            )

        if not name_appears_in_text(last_name, ocr_text):
            raise forms.ValidationError(
                "The last name could not be found on the ID. "
                "Check your spelling or upload a clearer image."
            )

        # The middle name is optional.
        # If entered, it must also match the ID.
        if (
            middle_name
            and not name_appears_in_text(middle_name, ocr_text)
        ):
            raise forms.ValidationError(
                "The middle name does not appear to match the ID. "
                "Check your spelling or leave the optional field blank."
            )

        # Return the file so Django can save it with the visitor record.
        file.seek(0)
        return file
