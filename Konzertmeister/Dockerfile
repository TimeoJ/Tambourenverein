# Nur für die Kommandozeile (PDF/Excel -> CSV), nicht für die GUI.
#   docker build -t km-importer .
#   docker run --rm -v "$PWD:/daten" km-importer /daten/programm.pdf --von 01.11.2026 --bis 31.12.2026 -o /daten/import.csv
FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir pdfplumber openpyxl
COPY . .
ENTRYPOINT ["python", "main.py"]
