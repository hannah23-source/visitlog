
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
    """
    Match every part of an entered name against OCR words.
    Allow minor OCR spelling differences.
    """
    normalized_name = normalize_text(name)
    normalized_text = normalize_text(ocr_text)

    if not normalized_name or not normalized_text:
        return False

    name_words = normalized_name.split()
    ocr_words = normalized_text.split()

    if not name_words or not ocr_words:
        return False

    # Every part of the entered name must match.
    for name_word in name_words:
        best_similarity = max(
            (
                SequenceMatcher(
                    None,
                    name_word,
                    ocr_word,
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
        print(
            "DEBUG: clean_id_document() reached",
            flush=True,
        )

        file = self.cleaned_data.get("id_document")

        if not file:
            raise forms.ValidationError(
                "Please upload or capture an image of your valid ID."
            )

        print(
            "DEBUG: ID filename:",
            file.name,
            flush=True,
        )

        # Accept JPG and PNG only.
        allowed_types = {
            "image/jpeg",
            "image/png",
        }

        if file.content_type not in allowed_types:
            raise forms.ValidationError(
                "Upload a JPG or PNG image only."
            )

        # Maximum upload size: 5 MB.
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "File size must not exceed 5 MB."
            )

        ocr_results = []

        try:
            # Confirm that the uploaded file is a valid image.
            file.seek(0)

            with Image.open(file) as original:
                original.verify()

            # Reopen and prepare the image for OCR.
            file.seek(0)

            with Image.open(file) as original:
                image = ImageOps.exif_transpose(original)
                image = ImageOps.grayscale(image)
                image = ImageEnhance.Contrast(image).enhance(1.5)

                # Enlarge the image to help read small text.
                image = image.resize(
                    (
                        image.width * 2,
                        image.height * 2,
                    )
                )

                # Try two OCR page segmentation modes.
                for psm in (6, 11):
                    ocr_text = pytesseract.image_to_string(
                        image,
                        lang="eng",
                        config=f"--oem 3 --psm {psm}",
                    )

                    ocr_results.append(ocr_text)

                    print(
                        f"OCR OUTPUT PSM {psm}:",
                        repr(ocr_text),
                        flush=True,
                    )

        except pytesseract.TesseractNotFoundError:
            print(
                "DEBUG ERROR: Tesseract executable not found.",
                flush=True,
            )

            raise forms.ValidationError(
                "ID verification is unavailable because Tesseract "
                "OCR is not installed or configured."
            )

        except pytesseract.TesseractError as error:
            print(
                "DEBUG ERROR: Tesseract failed:",
                str(error),
                flush=True,
            )

            raise forms.ValidationError(
                "Could not read the ID image. "
                "Please try a clearer photo."
            )

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
        ) as error:
            print(
                "DEBUG ERROR: Image processing failed:",
                str(error),
                flush=True,
            )

            raise forms.ValidationError(
                "The image could not be opened. "
                "Please upload a valid JPG or PNG."
            )

        finally:
            file.seek(0)

        # Combine OCR results to check for readable text.
        combined_ocr_text = "\n".join(ocr_results)

        print(
            "DEBUG: Combined OCR output:",
            repr(combined_ocr_text),
            flush=True,
        )

        if (
            not combined_ocr_text
            or len(normalize_text(combined_ocr_text)) < 3
        ):
            raise forms.ValidationError(
                "No readable text was found. "
                "Please take a clearer photo of your Student ID."
            )

        # Compare entered first and last names against both OCR results.
        # Middle name is optional and is not required for matching.
        first_name = self.cleaned_data.get("first_name", "")
        last_name = self.cleaned_data.get("last_name", "")

        first_matches = any(
            name_appears_in_text(first_name, text)
            for text in ocr_results
        )

        last_matches = any(
            name_appears_in_text(last_name, text)
            for text in ocr_results
        )

        print(
            "ENTERED FIRST NAME:",
            repr(first_name),
            flush=True,
        )

        print(
            "ENTERED LAST NAME:",
            repr(last_name),
            flush=True,
        )

        print(
            "FIRST NAME MATCH:",
            first_matches,
            flush=True,
        )

        print(
            "LAST NAME MATCH:",
            last_matches,
            flush=True,
        )

        # Require both the first and last names to match.
        if not first_matches or not last_matches:
            raise forms.ValidationError(
                "The name you entered does not match the name "
                "read from your ID. Please check your name and "
                "try a clear, well-lit photo of your Student ID."
            )

        file.seek(0)
        return file
