
import re
import unicodedata

from django import forms
from PIL import Image, ImageOps, ImageEnhance, UnidentifiedImageError
import pytesseract

from .models import Visitor


# Location ng Tesseract OCR sa Windows
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def normalize_text(text):
    """Gawing lowercase at alisin ang punctuation para madaling ikumpara."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )
    text = text.lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def name_appears_in_text(name, ocr_text):
    """Tingnan kung lumilitaw ang buong pangalan sa OCR text."""
    normalized_name = normalize_text(name)
    normalized_text = normalize_text(ocr_text)

    if not normalized_name:
        return False

    # Word sequence matching; hindi sapat ang partial word match.
    pattern = r"(?<!\w)" + re.escape(normalized_name) + r"(?!\w)"
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

        allowed_types = ["image/jpeg", "image/png"]

        if file.content_type not in allowed_types:
            if file.content_type == "application/pdf":
                raise forms.ValidationError(
                    "Automatic name checking currently supports JPG "
                    "and PNG only. Please upload an image of your ID."
                )

            raise forms.ValidationError(
                "Upload a JPG or PNG image only."
            )

        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "File size must not exceed 5 MB."
            )

        # Check the actual image and read its text with Tesseract.
        try:
            file.seek(0)

            with Image.open(file) as original:
                original.verify()

            file.seek(0)

            with Image.open(file) as original:
                image = ImageOps.grayscale(original)
                image = ImageEnhance.Contrast(image).enhance(1.5)
                image = image.resize(
                    (image.width * 2, image.height * 2)
                )

                ocr_text = pytesseract.image_to_string(
                    image,
                    lang="eng",
                    config="--psm 6",
                )

        except pytesseract.TesseractNotFoundError:
            raise forms.ValidationError(
                "Tesseract OCR was not found. Please check its installation."
            )
        except pytesseract.TesseractError:
            raise forms.ValidationError(
                "Could not read the ID image. Please try a clearer photo."
            )
        except (UnidentifiedImageError, OSError, ValueError):
            raise forms.ValidationError(
                "The image could not be opened. Please upload a valid JPG or PNG."
            )
        finally:
            file.seek(0)

        if not ocr_text or len(normalize_text(ocr_text)) < 3:
            raise forms.ValidationError(
                "No readable text was found. Please take a clearer photo "
                "of your ID."
            )

        # Match the visitor's first and last names.
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

        # Middle name is optional. If supplied, check it too.
        if middle_name and not name_appears_in_text(middle_name, ocr_text):
            raise forms.ValidationError(
                "The middle name does not appear to match the ID. "
                "Check your spelling or leave the optional field blank "
                "if appropriate."
            )

        # Suffixes such as Jr., Sr., II, and III are not required
        # to be entered in the form.
        return file
