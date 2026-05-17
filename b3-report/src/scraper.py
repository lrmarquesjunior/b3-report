"""
scraper.py
Faz login no investidor.b3.com.br e baixa os relatórios de posição.
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

load_dotenv(Path(__file__).parent.parent / ".env")

B3_URL = "https://www.investidor.b3.com.br/"
B3_CPF = os.getenv("B3_CPF")
B3_PASSWORD = os.getenv("B3_PASSWORD")
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"


def run_scraper() -> list[Path]:
    """
    Faz login na B3 e baixa os arquivos de posição consolidada.
    Retorna lista de caminhos dos arquivos baixados.
    """
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    downloaded_files: list[Path] = []

    # Caminho do Chrome instalado no sistema (passa melhor pelo Cloudflare)
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)

    with sync_playwright() as p:
        launch_kwargs = dict(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )
        if chrome_exe:
            print(f"[scraper] Usando Chrome do sistema: {chrome_exe}")
            launch_kwargs["executable_path"] = chrome_exe
        else:
            print("[scraper] Chrome não encontrado, usando Chromium do Playwright.")

        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        try:
            print("[scraper] Abrindo investidor.b3.com.br...")
            page.goto(B3_URL, wait_until="domcontentloaded", timeout=60_000)

            # Aguarda o Cloudflare liberar e a página estabilizar
            time.sleep(4)

            # --- Login (fluxo em duas etapas: CPF → Entrar → Senha → Entrar) ---
            print("[scraper] Preenchendo CPF...")
            cpf_input = page.wait_for_selector(
                'input[placeholder*="CPF"], input[placeholder*="CNPJ"], input[name*="cpf"], input[id*="cpf"]',
                timeout=20_000,
            )
            cpf_input.click()
            # Limpa o campo e digita só os números (a máscara do site formata automaticamente)
            cpf_digits = "".join(filter(str.isdigit, B3_CPF))
            cpf_input.type(cpf_digits, delay=100)
            time.sleep(1)

            # Aguarda o botão ficar habilitado
            page.wait_for_selector(
                'button:has-text("Entrar"):not([disabled]), button[type="submit"]:not([disabled])',
                timeout=10_000,
            )

            # Clica em Entrar para revelar o campo de senha
            page.click('button:has-text("Entrar"):not([disabled]), button[type="submit"]:not([disabled])')
            time.sleep(2)

            # Aguarda o campo de senha aparecer
            print("[scraper] Aguardando campo de senha...")
            pwd_input = page.wait_for_selector('input[type="password"]', timeout=20_000)
            pwd_input.click()
            pwd_input.type(B3_PASSWORD, delay=100)
            # Dispara eventos para ativar o botão
            pwd_input.dispatch_event("input")
            pwd_input.dispatch_event("change")
            time.sleep(1)

            # Submete com Enter (mais confiável que clicar no botão)
            pwd_input.press("Enter")
            page.wait_for_load_state("domcontentloaded", timeout=30_000)
            time.sleep(3)

            # --- Fecha popups se existirem ---
            try:
                page.click('button[aria-label="Close"], button[aria-label="Fechar"], button.close, [class*="close"]', timeout=5_000)
                time.sleep(1)
            except PlaywrightTimeout:
                pass  # sem popup, tudo bem

            # --- Navegar até Posição Consolidada via URL direta ---
            print("[scraper] Navegando para posição consolidada...")
            page.goto("https://www.investidor.b3.com.br/posicao-consolidada", wait_until="domcontentloaded", timeout=30_000)
            time.sleep(3)

            # --- Download do relatório ---
            print("[scraper] Baixando relatório...")
            with page.expect_download(timeout=30_000) as download_info:
                try:
                    page.click('button:has-text("Exportar"), a:has-text("Exportar"), button:has-text("Download")')
                except PlaywrightTimeout:
                    print("[scraper] Botão de exportar não encontrado — verifique os seletores.")
                    raise

            download = download_info.value
            dest = DOWNLOAD_DIR / download.suggested_filename
            download.save_as(dest)
            downloaded_files.append(dest)
            print(f"[scraper] Arquivo salvo: {dest}")

        except Exception as e:
            print(f"[scraper] ERRO: {e}")
            # Salva screenshot para debug
            screenshot_path = DOWNLOAD_DIR / "error_screenshot.png"
            page.screenshot(path=str(screenshot_path))
            print(f"[scraper] Screenshot salvo em: {screenshot_path}")
            raise

        finally:
            context.close()
            browser.close()

    return downloaded_files


if __name__ == "__main__":
    files = run_scraper()
    print(f"[scraper] Concluído. {len(files)} arquivo(s) baixado(s).")
