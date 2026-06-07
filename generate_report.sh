#!/bin/bash

# Скрипт для сборки и открытия Allure отчета

REPORTS_DIR="reports"
ALLURE_RESULTS="$REPORTS_DIR/allure-results"
ALLURE_REPORT="$REPORTS_DIR/allure-report"

echo "=== Сборка Allure отчета ==="

if [ ! -d "$ALLURE_RESULTS" ]; then
    echo "Ошибка: Директория с результатами ($ALLURE_RESULTS) не найдена. Сначала запустите пайплайн."
    exit 1
fi

# Проверка наличия allure в системе
if ! command -v allure &> /dev/null; then
    echo "Ошибка: Allure не установлен. Пожалуйста, установите его (brew install allure / apt install allure)."
    exit 1
fi

echo "Генерация отчета из $ALLURE_RESULTS..."
allure generate "$ALLURE_RESULTS" -o "$ALLURE_REPORT" --clean

echo "Отчет успешно сгенерирован в $ALLURE_REPORT"
echo "Чтобы открыть отчет, выполните: allure open $ALLURE_REPORT"
