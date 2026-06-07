"""
Test Generator - Модуль генерации тест-кейсов и автотестов
"""
import json
import logging
from typing import List, Dict
from qa_pipeline.llm_client import LLMClient
from qa_pipeline.config import CONFIG

logger = logging.getLogger(__name__)

class TestGenerator:
    """
    Генератор тестовых сценариев, JSON-контрактов и автотестов.
    """

    def __init__(self):
        self.llm = LLMClient()

    def generate_test_scenarios(self, checklist_content: str) -> List[Dict]:
        """
        Генерация JSON-контрактов тест-кейсов на основе чек-листа
        """
        prompt = f"""
        На основе следующего бизнес-чек-листа требований, сгенерируй JSON-список тест-кейсов.
        Каждый тест-кейс должен содержать: id, title, description, steps (список), expected_result.
        
        Чек-лист:
        {checklist_content}
        
        Верни ТОЛЬКО валидный JSON.
        """
        
        response = self.llm.generate(prompt)
        # Очистка от markdown, если есть
        json_str = response.replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)

    def generate_autotests(self, test_contracts: List[Dict]) -> str:
        """
        Генерация кода автотестов на основе JSON-контрактов
        """
        prompt = f"""
        На основе следующих JSON-контрактов тест-кейсов, сгенерируй код автотестов на языке Python (используя pytest).
        
        Контракты:
        {json.dumps(test_contracts, indent=2)}
        
        Сгенерируй полный, рабочий код файла с тестами.
        
        Требования к качеству кода (СТРОГО):
        1. Полное соответствие PEP-8.
        2. Ровно 2 пустые строки между импортами, классами и функциями на верхнем уровне.
        3. Никаких лишних пробелов на пустых строках.
        4. Максимальная длина строки - 79 символов. Переноси длинные строки, если необходимо.
        5. В конце файла обязательно должна быть одна пустая строка (newline).
        6. НЕ используй кастомные маркеры pytest типа `@pytest.mark.tc001`, так как они вызывают предупреждения. Вместо этого включай ID тест-кейса в название тестовой функции (например, `test_tc001_registration`) и подробно описывай шаги в docstring функции.
        
        Верни ТОЛЬКО чистый Python код в блоке кода.
        """
        
        response = self.llm.generate(prompt)
        # Очистка от markdown
        code = response.replace("```python", "").replace("```", "").strip()
        # Добавляем перенос строки в конце, если его нет
        if not code.endswith("\n"):
            code += "\n"
        return code

    def ai_code_review(self, code: str) -> str:
        """
        Этап AI-code-review сгенерированного кода
        """
        prompt = f"""
        Выполни AI-code-review следующего кода автотестов. 
        Проверь на соответствие лучшим практикам (Best Practices), читаемость, обработку ошибок и потенциальные баги.
        
        Код для ревью:
        {code}
        
        Верни результат ревью в структурированном виде (Markdown).
        """
        return self.llm.generate(prompt)

    def analyze_execution_results(self, logs: str, execution_data: dict) -> str:
        """
        AI-анализ логов и отчета о тестировании
        """
        prompt = f"""
        Проанализируй результаты выполнения тестов и предоставь краткое QA-summary.
        
        Данные о выполнении:
        {json.dumps(execution_data, indent=2)}
        
        Логи выполнения:
        {logs}
        
        Сформируй краткий отчет: что прошло успешно, что упало и почему, общие рекомендации.
        """
        return self.llm.generate(prompt)

    def generate_bug_report(self, failure_details: str) -> Dict:
        """
        Автоматическая генерация структурированного баг-репорта в формате JSON
        """
        prompt = f"""
        На основе следующей информации о падении теста, сформируй структурированный баг-репорт в формате JSON.
        
        Детали падения:
        {failure_details}
        
        JSON должен содержать: summary, steps_to_reproduce, actual_result, expected_result, severity, priority.
        Верни ТОЛЬКО валидный JSON.
        """
        response = self.llm.generate(prompt)
        json_str = response.replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)
