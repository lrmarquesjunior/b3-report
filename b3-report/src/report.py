"""
report.py
Gera relatório HTML com gráficos interativos (Plotly) a partir dos dados processados.
"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from jinja2 import Template
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Relatório B3 — {{ data_geracao }}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; color: #333; }
    header { background: #1a1a2e; color: white; padding: 24px 32px; }
    header h1 { font-size: 1.6rem; }
    header p  { font-size: 0.9rem; opacity: 0.7; margin-top: 4px; }
    .container { max-width: 1100px; margin: 32px auto; padding: 0 16px; }
    .cards { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 32px; }
    .card {
      background: white; border-radius: 10px; padding: 20px 24px;
      flex: 1; min-width: 180px; box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    }
    .card .label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
    .card .value { font-size: 1.6rem; font-weight: 700; margin-top: 6px; color: #1a1a2e; }
    .card .value.positive { color: #27ae60; }
    .card .value.negative { color: #e74c3c; }
    .section { background: white; border-radius: 10px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
    .section h2 { font-size: 1.1rem; margin-bottom: 16px; color: #1a1a2e; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th { background: #f8f9fa; text-align: left; padding: 10px 12px; font-weight: 600; color: #555; }
    td { padding: 9px 12px; border-bottom: 1px solid #f0f0f0; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #fafbfc; }
    footer { text-align: center; padding: 24px; font-size: 0.8rem; color: #aaa; }
  </style>
</head>
<body>
  <header>
    <h1>📊 Relatório de Investimentos — B3</h1>
    <p>Gerado em {{ data_geracao }}</p>
  </header>

  <div class="container">

    <!-- Cards de resumo -->
    <div class="cards">
      <div class="card">
        <div class="label">Patrimônio Total</div>
        <div class="value">{{ patrimonio_total }}</div>
      </div>
      <div class="card">
        <div class="label">Nº de Ativos</div>
        <div class="value">{{ num_ativos }}</div>
      </div>
      <div class="card">
        <div class="label">Tipos de Ativo</div>
        <div class="value">{{ num_tipos }}</div>
      </div>
    </div>

    <!-- Gráfico: Pizza por tipo de ativo -->
    {% if grafico_pizza %}
    <div class="section">
      <h2>Distribuição por Tipo de Ativo</h2>
      {{ grafico_pizza }}
    </div>
    {% endif %}

    <!-- Gráfico: Barras por emissor -->
    {% if grafico_barras %}
    <div class="section">
      <h2>Top Emissores / Ativos (por valor)</h2>
      {{ grafico_barras }}
    </div>
    {% endif %}

    <!-- Tabela de posição completa -->
    {% if tabela_posicao %}
    <div class="section">
      <h2>Posição Consolidada</h2>
      {{ tabela_posicao }}
    </div>
    {% endif %}

  </div>

  <footer>Dados extraídos de investidor.b3.com.br · Uso pessoal</footer>
</body>
</html>
"""


def _fmt_brl(value: float) -> str:
    """Formata valor como moeda BRL."""
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(value)


def _df_to_html_table(df: pd.DataFrame, money_cols: list[str] = None) -> str:
    """Converte DataFrame para tabela HTML estilizada."""
    if df.empty:
        return "<p>Sem dados disponíveis.</p>"

    df_display = df.copy()
    if money_cols:
        for col in money_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(
                    lambda x: _fmt_brl(x) if pd.notna(x) else "-"
                )

    return df_display.to_html(index=False, border=0, classes="", escape=False)


def generate_report(data: dict, output_dir: Path = OUTPUT_DIR) -> Path:
    """
    Gera o relatório HTML e salva em output_dir.

    Args:
        data: dicionário retornado por processor.process()
        output_dir: pasta de saída

    Returns:
        Path do arquivo HTML gerado
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    df_posicao  = data.get("posicao", pd.DataFrame())
    df_por_tipo = data.get("por_tipo", pd.DataFrame())
    df_emissor  = data.get("por_emissor", pd.DataFrame())

    data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")

    # --- Métricas de resumo ---
    patrimonio_total = _fmt_brl(
        df_posicao["valor_atualizado"].sum() if "valor_atualizado" in df_posicao.columns else 0
    )
    num_ativos = len(df_posicao)
    num_tipos  = df_posicao["tipo_ativo"].nunique() if "tipo_ativo" in df_posicao.columns else "-"

    # --- Gráfico pizza: distribuição por tipo ---
    grafico_pizza = ""
    if not df_por_tipo.empty and "tipo_ativo" in df_por_tipo.columns:
        fig = px.pie(
            df_por_tipo,
            names="tipo_ativo",
            values="valor_atualizado",
            color_discrete_sequence=px.colors.qualitative.Set3,
            hole=0.35,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=420,
            showlegend=True,
            legend=dict(orientation="v", x=1.02),
        )
        grafico_pizza = fig.to_html(full_html=False, include_plotlyjs="cdn")

    # --- Gráfico barras: top emissores ---
    grafico_barras = ""
    if not df_emissor.empty and "emissor" in df_emissor.columns:
        fig2 = px.bar(
            df_emissor.sort_values("valor_atualizado"),
            x="valor_atualizado",
            y="emissor",
            orientation="h",
            color="valor_atualizado",
            color_continuous_scale="Blues",
            labels={"valor_atualizado": "Valor (R$)", "emissor": ""},
        )
        fig2.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=max(300, len(df_emissor) * 32),
            coloraxis_showscale=False,
        )
        grafico_barras = fig2.to_html(full_html=False, include_plotlyjs=False)

    # --- Tabela de posição ---
    tabela_posicao = _df_to_html_table(
        df_posicao,
        money_cols=["valor_atualizado", "preco_medio", "resultado"],
    )

    # --- Renderiza template ---
    template = Template(HTML_TEMPLATE)
    html_content = template.render(
        data_geracao=data_geracao,
        patrimonio_total=patrimonio_total,
        num_ativos=num_ativos,
        num_tipos=num_tipos,
        grafico_pizza=grafico_pizza,
        grafico_barras=grafico_barras,
        tabela_posicao=tabela_posicao,
    )

    # --- Salva arquivo ---
    filename = f"relatorio_b3_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    output_path = output_dir / filename
    output_path.write_text(html_content, encoding="utf-8")
    print(f"[report] Relatório gerado: {output_path}")

    return output_path


if __name__ == "__main__":
    from processor import process
    data = process()
    generate_report(data)
