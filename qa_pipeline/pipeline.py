"""
AI-Driven QA Pipeline - Главный оркестратор
"""
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Dict
from qa_pipeline.config import CONFIG, BASE_DIR, REPORTS_DIR, ARTIFACTS_DIR, ALLURE_RESULTS_DIR, TEMP_TESTS_DIR
from qa_pipeline.pii_guardrails import PIIGuardrails
from qa_pipeline.test_generator import TestGenerator

logger = logging.getLogger(__name__)


class QAPipeline:
    """
    Главный класс AI-Driven QA пайплайна.
    Оркестрирует все этапы: от загрузки чек-листа до формирования баг-репортов.
    """

    def __init__(self):
        self.pii_guardrails = PIIGuardrails()
        self.test_generator = TestGenerator()
        self.artifacts = {}
        self.results = {
            "status": "pending",
            "stages": {},
            "errors": [],
            "summary": {}
        }
        logger.info("QAPipeline initialized")

    def run(self, checklist_path: Optional[str] = None) -> dict:
        """
        Запуск полного пайплайна

        Args:
            checklist_path: Путь к файлу с бизнес-чек-листом

        Returns:
            Dict с результатами всех этапов
        """
        logger.info("=" * 60)
        logger.info("STARTING AI-DRIVEN QA PIPELINE")
        logger.info("=" * 60)

        try:
            # Этап 0: Проверка входных данных
            checklist_data = self._load_checklist(checklist_path)

            # Этап 1: PII Guardrails
            pii_result = self._stage_pii_check(checklist_data)

            # Этап 2: Генерация тест-кейсов
            test_contracts = self._stage_generate_test_contracts(pii_result.masked_content)

            # Этап 3: Генерация автотестов
            test_file = self._stage_generate_autotests(test_contracts)

            # Этап 4: Linting
            self._stage_linting(test_file)

            # Этап 5: AI Code Review
            with open(test_file, "r", encoding="utf-8") as f:
                code = f.read()
            self._stage_ai_code_review(code)

            # Этап 6: Выполнение тестов
            execution_results = self._stage_execute_tests(test_file)

            # Этап 7: AI Анализ и Баг-репорт
            self._stage_ai_analysis(execution_results)

            self.results["status"] = "passed" if execution_results["status"] == "passed" else "failed"
            logger.info("=" * 60)
            logger.info("QA PIPELINE COMPLETED")
            logger.info("=" * 60)

        except Exception as e:
            self.results["status"] = "failed"
            self.results["errors"].append(str(e))
            logger.error(f"Pipeline failed: {e}", exc_info=True)

        return self.results

    def _load_checklist(self, checklist_path: Optional[str] = None) -> str:
        """Загрузка чек-листа требований"""
        path = checklist_path or CONFIG.checklist_path
        path_obj = Path(path)

        if not path_obj.exists():
            logger.warning(f"Checklist not found at {path}, using sample data")
            return json.dumps({
                "requirements": [
                    {"id": "REQ-001", "description": "Пользователь может зарегистрироваться"},
                    {"id": "REQ-002", "description": "Пользователь может войти в систему"},
                    {"id": "REQ-003", "description": "Система проверяет email при регистрации"}
                ]
            })

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.info(f"Checklist loaded: {path}")
        return content

    def _stage_pii_check(self, content: str) -> object:
        """Этап 1: Проверка PII и маскирование"""
        logger.info("[Stage 1/7] PII Guardrails Check")

        result = self.pii_guardrails.mask_pii(content)

        if result.has_pii:
            logger.info(f"  PII detected and masked: {result.pii_count} instances")
            self.artifacts["pii_report"] = self.pii_guardrails.generate_pii_report(result)
        else:
            logger.info("  No PII detected")

        # Сохраняем артефакт
        artifact_path = ARTIFACTS_DIR / "pii_report.json"
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(self.artifacts.get("pii_report", {"has_pii": False}), f, indent=2, ensure_ascii=False)

        self.results["stages"]["pii_check"] = {
            "status": "passed",
            "has_pii": result.has_pii,
            "count": result.pii_count
        }

        return result

    def _stage_generate_test_contracts(self, content: str) -> List[Dict]:
        """Этап 2: Генерация тест-кейсов (JSON контрактов)"""
        logger.info("[Stage 2/7] Generating Test Contracts")
        contracts = self.test_generator.generate_test_scenarios(content)
        
        artifact_path = ARTIFACTS_DIR / "test_contracts.json"
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(contracts, f, indent=2, ensure_ascii=False)
            
        self.results["stages"]["test_contracts"] = {"status": "passed", "count": len(contracts)}
        return contracts

    def _stage_generate_autotests(self, contracts: List[Dict]) -> str:
        """Этап 3: Генерация кода автотестов"""
        logger.info("[Stage 3/7] Generating Autotests")
        test_code = self.test_generator.generate_autotests(contracts)
        
        test_file_path = Path(CONFIG.test_output_dir) / "generated_test.py"
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(test_code)
            
        self.results["stages"]["autotests"] = {"status": "passed", "file": str(test_file_path)}
        return str(test_file_path)

    def _stage_linting(self, test_file_path: str) -> bool:
        """Этап 4: Проверка качества кода (Linting)"""
        logger.info("[Stage 4/7] Linting Generated Code")
        result = subprocess.run(
            [sys.executable, "-m", "flake8", test_file_path],
            capture_output=True,
            text=True
        )
        
        status = "passed" if result.returncode == 0 else "failed"
        self.results["stages"]["linting"] = {
            "status": status,
            "output": result.stdout + result.stderr
        }
        
        logger.info(f"Linting completed with status: {status}")
        return result.returncode == 0

    def _stage_execute_tests(self, test_file_path: str) -> dict:
        """Этап 6: Выполнение тестов"""
        logger.info("[Stage 6/7] Executing Tests")
        
        # Запуск pytest с allure
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            test_file_path,
            f"--alluredir={ALLURE_RESULTS_DIR}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        status = "passed" if result.returncode == 0 else "failed"
        self.results["stages"]["execution"] = {
            "status": status,
            "output": result.stdout + result.stderr
        }
        
        logger.info(f"Tests executed with status: {status}")
        return self.results["stages"]["execution"]

    def _stage_ai_code_review(self, code: str) -> str:
        """Этап 5: AI Code Review"""
        logger.info("[Stage 5/7] AI Code Review")
        review_result = self.test_generator.ai_code_review(code)
        
        artifact_path = ARTIFACTS_DIR / "ai_code_review.md"
        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(review_result)
            
        self.results["stages"]["ai_review"] = {"status": "passed", "artifact": str(artifact_path)}
        return review_result

    def _stage_ai_analysis(self, execution_results: dict) -> None:
        """Этап 7: AI Анализ логов и генерация баг-репортов"""
        logger.info("[Stage 7/7] AI Analysis & Bug Reporting")
        
        logs = execution_results.get("output", "")
        summary = self.test_generator.analyze_execution_results(logs, execution_results)
        
        # Сохраняем summary
        summary_path = ARTIFACTS_DIR / "qa_summary.md"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
            
        self.results["summary"] = summary
        
        # Если есть падения, генерируем баг-репорт
        if execution_results["status"] == "failed":
            logger.info("  Tests failed, generating bug report...")
            bug_report = self.test_generator.generate_bug_report(logs)
            
            bug_report_path = ARTIFACTS_DIR / "bug_report.json"
            with open(bug_report_path, "w", encoding="utf-8") as f:
                json.dump(bug_report, f, indent=2, ensure_ascii=False)
                
            self.results["bug_report"] = bug_report
            logger.info(f"  Bug report generated: {bug_report_path}")

        self.results["stages"]["ai_analysis"] = {"status": "passed"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pipeline = QAPipeline()
    results = pipeline.run()
    print(json.dumps(results, indent=2, ensure_ascii=False))
