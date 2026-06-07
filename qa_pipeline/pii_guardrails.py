"""
PII Guardrails - Модуль обнаружения и маскирования чувствительных данных
"""
import re
import json
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, field

from qa_pipeline.config import CONFIG

logger = logging.getLogger(__name__)


@dataclass
class PIIDetectionResult:
    """Результат обнаружения PII"""
    has_pii: bool = False
    detected_fields: Dict[str, List[str]] = field(default_factory=dict)
    masked_content: str = ""
    original_content: str = ""
    pii_count: int = 0


class PIIGuardrails:
    """
    Guardrails для обнаружения и маскирования PII данных.
    Поддерживает: email, телефон, паспорт, кредитные карты, СНИЛС, ИНН
    """

    def __init__(self, patterns: Optional[Dict[str, str]] = None):
        self.patterns = patterns or CONFIG.pii_patterns
        self.mask_char = CONFIG.pii_mask_char
        self._compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.patterns.items()
        }
        logger.info(f"PII Guardrails initialized with patterns: {list(self.patterns.keys())}")

    def detect_pii(self, content: str) -> PIIDetectionResult:
        """
        Обнаружение PII в тексте

        Args:
            content: Текст для проверки

        Returns:
            PIIDetectionResult с результатами обнаружения
        """
        result = PIIDetectionResult(original_content=content)
        detected_fields = {}

        for pii_type, pattern in self._compiled_patterns.items():
            matches = pattern.findall(content)
            if matches:
                detected_fields[pii_type] = list(set(matches))
                result.has_pii = True
                result.pii_count += len(matches)

        result.detected_fields = detected_fields

        if result.has_pii:
            logger.warning(f"PII detected: {result.pii_count} instances in {len(detected_fields)} categories")
            for pii_type, values in detected_fields.items():
                logger.debug(f"  {pii_type}: {values}")
        else:
            logger.info("No PII detected in content")

        return result

    def mask_pii(self, content: str) -> PIIDetectionResult:
        """
        Маскирование PII в тексте

        Args:
            content: Исходный текст

        Returns:
            PIIDetectionResult с замаскированным текстом
        """
        result = self.detect_pii(content)
        masked = content

        for pii_type, pattern in self._compiled_patterns.items():
            def mask_match(match, pii_type=pii_type):
                matched_text = match.group(0)
                # Сохраняем первый и последний символ для наглядности
                if len(matched_text) <= 3:
                    return self.mask_char * len(matched_text)
                # Маскируем середину, оставляя начало и конец
                visible_chars = 2
                masked_part = self.mask_char * (len(matched_text) - visible_chars * 2)
                return matched_text[:visible_chars] + masked_part + matched_text[-visible_chars:]

            masked = pattern.sub(mask_match, masked)

        result.masked_content = masked

        if result.has_pii:
            logger.info(f"PII masked successfully: {result.pii_count} instances")
        else:
            result.masked_content = content

        return result

    def validate_file(self, file_path: str) -> PIIDetectionResult:
        """
        Проверка файла на наличие PII

        Args:
            file_path: Путь к файлу

        Returns:
            PIIDetectionResult с результатами
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        return self.mask_pii(content)

    def create_masked_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Создание файла с замаскированными PII

        Args:
            input_path: Путь к исходному файлу
            output_path: Путь для сохранения (если None, добавляется суффикс _masked)

        Returns:
            Путь к созданному файлу
        """
        input_path = Path(input_path)
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_masked{input_path.suffix}"

        result = self.validate_file(str(input_path))

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.masked_content)

        logger.info(f"Masked file created: {output_path}")
        return str(output_path)

    def generate_pii_report(self, result: PIIDetectionResult) -> dict:
        """
        Генерация отчета об обнаруженных PII

        Args:
            result: Результат обнаружения PII

        Returns:
            Словарь с отчетом
        """
        return {
            "has_pii": result.has_pii,
            "total_pii_count": result.pii_count,
            "pii_categories": {
                pii_type: {
                    "count": len(values),
                    "examples": values[:3],  # Показываем только первые 3 примера
                }
                for pii_type, values in result.detected_fields.items()
            },
            "masking_applied": result.original_content != result.masked_content,
            "recommendation": "PII detected - manual review recommended" if result.has_pii else "No PII issues",
        }