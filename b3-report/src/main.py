"""
main.py
Ponto de entrada principal — orquestra scraper → processor → report → uploader.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Garante que o diretório de logs existe antes de configurar o logging
Path("logs").mkdir(exist_ok=True)

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Iniciando coleta B3 ===")

    # 1. Scraper — login e download
    try:
        from scraper import run_scraper
        downloaded = run_scraper()
        logger.info(f"Scraper concluído. {len(downloaded)} arquivo(s) baixado(s).")
    except Exception as e:
        logger.error(f"Falha no scraper: {e}")
        sys.exit(1)

    # 2. Processor — processa os arquivos
    try:
        from processor import process
        data = process()
        logger.info("Processamento concluído.")
    except FileNotFoundError as e:
        logger.error(f"Nenhum arquivo para processar: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Falha no processamento: {e}")
        sys.exit(1)

    # 3. Report — gera HTML
    try:
        from report import generate_report
        import os
        output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
        report_path = generate_report(data, output_dir)
        logger.info(f"Relatório gerado: {report_path}")
    except Exception as e:
        logger.error(f"Falha na geração do relatório: {e}")
        sys.exit(1)

    # 4. Uploader — envia para o Google Drive
    try:
        from uploader import upload_report
        upload_report(output_dir)
        logger.info("Upload para o Google Drive concluído.")
    except Exception as e:
        logger.error(f"Falha no upload: {e}")
        sys.exit(1)

    logger.info("=== Coleta B3 finalizada com sucesso ===")


if __name__ == "__main__":
    # Garante que o diretório de logs existe
    Path("logs").mkdir(exist_ok=True)
    main()
