"""
token_shredder - Dockerfile Converter
Converts Dockerfiles to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger
import re

logger = setup_logger(__name__)


class DockerfileConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.dockerfile', 'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='dockerfile',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            markdown_parts.append(f"# Docker: {file_path}")
            markdown_parts.append("")

            stages = []

            # Check if it's docker-compose
            if 'version:' in content.lower() or 'services:' in content.lower():
                markdown_parts.append("## Type: Docker Compose")
                markdown_parts.append("")

                # Extract services
                services = re.findall(r'services:\\s*\\n((?:[^}]+\\n)*)', content, re.MULTILINE)
                if services:
                    markdown_parts.append("## Services")
                    for svc in services[:10]:  # Limit
                        service_name = re.search(r'(\\w+):', svc)
                        if service_name:
                            markdown_parts.append(f"- `{service_name.group(1)}`")
                    markdown_parts.append("")

                # Extract images
                images = re.findall(r'image:\\s*([^\\n]+)', content)
                if images:
                    markdown_parts.append("## Images")
                    for img in images[:10]:
                        markdown_parts.append(f"- `{img.strip()}`")
                    markdown_parts.append("")
            else:
                # Regular Dockerfile
                markdown_parts.append("## Type: Dockerfile")
                markdown_parts.append("")

                # Extract stages
                stages = re.findall(r'^(FROM|RUN|COPY|ADD|WORKDIR|ENV|ARG|EXPOSE|VOLUME|CMD|ENTRYPOINT|LABEL|USER|HEALTHCHECK|SHELL)', content, re.MULTILINE)
                stage_counts = {}
                for s in stages:
                    stage_counts[s] = stage_counts.get(s, 0) + 1

                markdown_parts.append("## Instructions")
                for instr, count in sorted(stage_counts.items(), key=lambda x: -x[1]):
                    markdown_parts.append(f"- `{instr}`: {count}")
                markdown_parts.append("")

                # Extract base image
                base = re.search(r'^FROM\\s+(.+?)(?:\\s+AS\\s+\\w+)?$', content, re.MULTILINE)
                if base:
                    markdown_parts.append(f"## Base Image")
                    markdown_parts.append(f"`{base.group(1).strip()}`")
                    markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading Dockerfile: {e}")
            markdown_parts.append(f"[Error reading Dockerfile: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                content = f.read()
            lines = len(content.splitlines())
            return {'lines': lines, 'type': 'compose' if 'services:' in content.lower() else 'dockerfile'}
        except:
            return {'lines': 0, 'type': 'unknown'}
