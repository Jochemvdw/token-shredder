"""
token_shredder - Image Handler Processor
Handles image references vs embedding
"""
import base64
import os
import io
from pathlib import Path
from typing import Optional
from docx import Document as DocxDocument
from pptx import Presentation as PptxPresentation
from pptx.util import Inches


class ImageHandler:
    def __init__(self, max_image_size: int = 1048576):
        self.max_image_size = max_image_size

    def process(self, content: str, file_path: str, embed: bool = False) -> str:
        """Process images in content."""
        if embed:
            return self._embed_images(content, file_path)
        else:
            return self._reference_images(content, file_path)

    def _embed_images(self, content: str, file_path: str) -> str:
        """Embed images as base64 from DOCX/PPTX files."""
        path = Path(file_path)
        embedded = []

        try:
            if path.suffix.lower() == '.docx':
                doc = DocxDocument(file_path)
                for rel in doc.part.rels.values():
                    if "image" in rel.target_ref:
                        image_part = rel.target_part
                        image_data = image_part.blob
                        if len(image_data) <= self.max_image_size:
                            b64 = base64.b64encode(image_data).decode()
                            embedded.append(f"![Embedded Image](data:image/{self._get_image_type(rel.target_ref)};base64,{b64})")
            elif path.suffix.lower() == '.pptx':
                prs = PptxPresentation(file_path)
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "image"):
                            image = shape.image
                            image_data = image.blob
                            if len(image_data) <= self.max_image_size:
                                b64 = base64.b64encode(image_data).decode()
                                embedded.append(f"![Embedded Image](data:image/{self._get_image_type(image.content_type)};base64,{b64})")
        except Exception as e:
            pass

        for img in embedded:
            content = content.replace(img.split(']')[0] + ']', img)

        return content

    def _reference_images(self, content: str, file_path: str) -> str:
        """Reference images by relative path."""
        path = Path(file_path).resolve()
        parent = path.parent
        if not parent:
            return content
        parent_str = str(parent)
        result = content
        idx = 0
        while True:
            idx = result.find(parent_str, idx)
            if idx == -1:
                break
            end = idx + len(parent_str)
            result = result[:idx] + "./images" + result[end:]
            idx += len("./images")
        return result

    def _get_image_type(self, content_type: str) -> str:
        """Get image type from content type."""
        type_map = {
            'image/png': 'png',
            'image/jpeg': 'jpeg',
            'image/gif': 'gif',
            'image/svg+xml': 'svg',
        }
        return type_map.get(content_type, 'png')
