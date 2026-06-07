"""
Конфигурация AI-driven QA пайплайна
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Базовые пути
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR
TEST_DATA_DIR = BASE_DIR / "test_data"
REPORTS_DIR = BASE_DIR / "reports"
ARTIFACTS_DIR = REPORTS_DIR / "artifacts"
ALLURE_RESULTS_DIR = REPORTS_DIR / "allure-results"
ALLURE_REPORT_DIR = REPORTS_DIR / "allure-report"
TEMP_TESTS_DIR = BASE_DIR / "generated_tests"
LOGS_DIR = REPORTS_DIR / "logs"
CHECKLISTS_DIR = TEST_DATA_DIR / "checklists"


@dataclass
class LLMConfig:
    """Конфигурация LLM модели"""
    api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    model_name: str = "gemini-3-flash-preview"
    temperature: float = 0.3
    max_output_tokens: int = 4096


@dataclass
class PipelineConfig:
    """Конфигурация пайплайна"""
    # LLM
    llm: LLMConfig = field(default_factory=LLMConfig)

    # PII Guardrails
    pii_patterns: dict = field(default_factory=lambda: {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\+?7[ -]?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}",
        "passport": r"\d{2}[ -]?\d{2}[ -]?\d{6}",
        "credit_card": r"\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}",
        "snils": r"\d{3}[ -]?\d{3}[ -]?\d{3}[ -]?\d{2}",
        "inn": r"\d{10,12}",
    })
    pii_mask_char: str = "*"

    # Test Generation
    test_framework: str = "pytest"
    test_runner: str = "pytest"

    # Code Quality
    linting_enabled: bool = True
    linting_tools: list = field(default_factory=lambda: ["pylint", "flake8"])

    # CI
    ci_enabled: bool = True
    ci_type: str = "github_actions"

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Paths
    checklist_path: str = str(CHECKLISTS_DIR / "sample_checklist.json")
    test_output_dir: str = str(TEMP_TESTS_DIR)
    report_dir: str = str(REPORTS_DIR)
    allure_results_dir: str = str(ALLURE_RESULTS_DIR)
    logs_dir: str = str(LOGS_DIR)

    def __post_init__(self):
        """Создание необходимых директорий"""
        for path in [
            TEST_DATA_DIR, REPORTS_DIR, ARTIFACTS_DIR,
            ALLURE_RESULTS_DIR, TEMP_TESTS_DIR, LOGS_DIR, CHECKLISTS_DIR
        ]:
            path.mkdir(parents=True, exist_ok=True)


# Глобальный экземпляр конфигурации
CONFIG = PipelineConfig()