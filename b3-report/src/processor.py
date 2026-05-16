"""
processor.py
Processa os arquivos baixados da B3 e retorna DataFrames consolidados.
"""

import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))


def load_files(download_dir: Path = DOWNLOAD_DIR) -> list[pd.DataFrame]:
    """Carrega todos os CSVs/XLS da pasta de downloads."""
    frames = []
    for f in sorted(download_dir.glob("*")):
        if f.suffix.lower() in (".csv", ".xls", ".xlsx"):
            print(f"[processor] Carregando: {f.name}")
            try:
                if f.suffix.lower() == ".csv":
                    df = pd.read_csv(f, sep=None, engine="python", encoding="utf-8-sig")
                else:
                    df = pd.read_excel(f)
                frames.append(df)
            except Exception as e:
                print(f"[processor] Erro ao carregar {f.name}: {e}")
    return frames


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes de colunas para lowercase sem espaços."""
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("/", "_")
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("ascii")
    )
    return df


def process(download_dir: Path = DOWNLOAD_DIR) -> dict[str, pd.DataFrame]:
    """
    Processa os arquivos e retorna um dicionário com DataFrames prontos para o relatório.

    Retorna:
        {
            "posicao":    DataFrame com posição consolidada por ativo,
            "por_tipo":   DataFrame agrupado por tipo de ativo,
            "por_emissor": DataFrame agrupado por emissor,
        }
    """
    frames = load_files(download_dir)
    if not frames:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em {download_dir}")

    # Concatena todos os arquivos (caso haja mais de um)
    df = pd.concat(frames, ignore_index=True)
    df = normalize_columns(df)

    print(f"[processor] Colunas disponíveis: {list(df.columns)}")
    print(f"[processor] Total de linhas: {len(df)}")

    # --- Identifica colunas principais (adapta conforme o layout real da B3) ---
    # Mapeamento flexível: tenta encontrar colunas pelo nome parcial
    col_map = _detect_columns(df)
    print(f"[processor] Mapeamento de colunas: {col_map}")

    # Renomeia para nomes padronizados
    df = df.rename(columns={v: k for k, v in col_map.items() if v})

    # Converte valores numéricos
    for col in ["valor_atualizado", "quantidade", "preco_medio", "resultado"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("R$", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Remove linhas sem valor
    if "valor_atualizado" in df.columns:
        df = df.dropna(subset=["valor_atualizado"])
        df = df[df["valor_atualizado"] > 0]

    # Agrupamentos
    por_tipo = pd.DataFrame()
    por_emissor = pd.DataFrame()

    if "tipo_ativo" in df.columns and "valor_atualizado" in df.columns:
        por_tipo = (
            df.groupby("tipo_ativo")["valor_atualizado"]
            .sum()
            .reset_index()
            .sort_values("valor_atualizado", ascending=False)
        )

    if "emissor" in df.columns and "valor_atualizado" in df.columns:
        por_emissor = (
            df.groupby("emissor")["valor_atualizado"]
            .sum()
            .reset_index()
            .sort_values("valor_atualizado", ascending=False)
            .head(15)  # top 15
        )

    return {
        "posicao": df,
        "por_tipo": por_tipo,
        "por_emissor": por_emissor,
    }


def _detect_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """
    Tenta mapear colunas do arquivo da B3 para nomes padronizados.
    Ajuste os padrões conforme o layout real do arquivo exportado.
    """
    cols = list(df.columns)

    def find(patterns: list[str]) -> str | None:
        for pat in patterns:
            for col in cols:
                if pat in col:
                    return col
        return None

    return {
        "tipo_ativo":        find(["tipo", "produto", "categoria", "classe"]),
        "emissor":           find(["emissor", "empresa", "ativo", "ticker", "codigo"]),
        "quantidade":        find(["quantidade", "qtd", "qtde"]),
        "preco_medio":       find(["preco_medio", "preco", "custo_medio"]),
        "valor_atualizado":  find(["valor_atualizado", "valor_atual", "saldo", "total"]),
        "resultado":         find(["resultado", "ganho", "lucro", "rentabilidade"]),
    }


if __name__ == "__main__":
    data = process()
    for key, df in data.items():
        print(f"\n--- {key} ---")
        print(df.head())
