"""
uploader.py
Faz upload do relatório HTML para o Google Drive usando Service Account.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv(Path(__file__).parent.parent / ".env")

CREDENTIALS_PATH  = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
DRIVE_FOLDER_ID   = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
SCOPES            = ["https://www.googleapis.com/auth/drive.file"]


def _get_service():
    """Autentica com a Service Account e retorna o cliente do Drive."""
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def upload_file(file_path: Path, keep_versions: int = 5) -> str:
    """
    Faz upload de um arquivo para o Google Drive.

    - Se já existir um arquivo com o mesmo nome na pasta, cria uma nova versão.
    - Mantém apenas as últimas `keep_versions` versões (remove as mais antigas).

    Args:
        file_path:     caminho local do arquivo a enviar
        keep_versions: quantas versões manter no Drive

    Returns:
        ID do arquivo no Google Drive
    """
    if not DRIVE_FOLDER_ID:
        raise ValueError("GOOGLE_DRIVE_FOLDER_ID não configurado no .env")

    service = _get_service()
    filename = file_path.name
    mimetype = "text/html"

    print(f"[uploader] Enviando '{filename}' para o Google Drive...")

    # Verifica arquivos existentes com o mesmo nome na pasta
    query = (
        f"name='{filename}' and "
        f"'{DRIVE_FOLDER_ID}' in parents and "
        f"trashed=false"
    )
    existing = service.files().list(
        q=query,
        fields="files(id, name, createdTime)",
        orderBy="createdTime desc",
    ).execute().get("files", [])

    # Upload do novo arquivo
    file_metadata = {
        "name": filename,
        "parents": [DRIVE_FOLDER_ID],
    }
    media = MediaFileUpload(str(file_path), mimetype=mimetype, resumable=True)
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink",
    ).execute()

    file_id   = uploaded["id"]
    view_link = uploaded.get("webViewLink", "")
    print(f"[uploader] Upload concluído. ID: {file_id}")
    print(f"[uploader] Link: {view_link}")

    # Remove versões antigas além do limite
    if len(existing) >= keep_versions:
        to_delete = existing[keep_versions - 1:]
        for old_file in to_delete:
            service.files().delete(fileId=old_file["id"]).execute()
            print(f"[uploader] Versão antiga removida: {old_file['id']} ({old_file['createdTime']})")

    return file_id


def upload_report(output_dir: Path) -> None:
    """Faz upload de todos os HTMLs na pasta de output."""
    html_files = sorted(output_dir.glob("*.html"), reverse=True)
    if not html_files:
        print("[uploader] Nenhum arquivo HTML encontrado para upload.")
        return

    # Envia apenas o mais recente
    latest = html_files[0]
    upload_file(latest)


if __name__ == "__main__":
    from pathlib import Path
    upload_report(Path(os.getenv("OUTPUT_DIR", "output")))
