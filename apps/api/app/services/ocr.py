import base64

from mistralai.client import Mistral

from ..config import settings
from .mistral_client import retry_mistral


class OCRService:
    """Document text extraction, powered by Mistral's OCR API."""

    def __init__(self) -> None:
        self._client = Mistral(api_key=settings.mistral_api_key)

    @retry_mistral
    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        b64 = base64.b64encode(file_bytes).decode()
        data_uri = f"data:{mime_type};base64,{b64}"
        is_image = mime_type.startswith("image/")
        document = (
            {"type": "image_url", "image_url": data_uri}
            if is_image
            else {"type": "document_url", "document_url": data_uri}
        )

        response = self._client.ocr.process(model="mistral-ocr-latest", document=document)
        return "\n\n".join(page.markdown for page in response.pages).strip()


ocr_service = OCRService()
