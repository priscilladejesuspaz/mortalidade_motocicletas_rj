# ================================================================================
# PROJETO FINAL EBAC — Análise de Mortalidade de Motociclistas
# Município do Rio de Janeiro | 2003–2024
# Fonte: Base dos Dados · SIM/MS · DENATRAN
# ================================================================================

from google.cloud import bigquery
import pandas as pd
import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

# ================================================================================
# CONFIGURAÇÃO DO PROJETO E FONTES DE DADOS
# ================================================================================

PROJECT_ID = "projetofinalebac-505021"
DATASET = "dados_mortalidade"

# Views criadas no BigQuery com os dados filtrados para o município do RJ
VW_FROTA = f"`{PROJECT_ID}.{DATASET}.vw_frota_motos_rj_ready`"
VW_MORTALIDADE = f"`{PROJECT_ID}.{DATASET}.vw_mortalidade_motociclistas_rj_ready`"
VW_POPULACAO = f"`{PROJECT_ID}.{DATASET}.vw_populacao_rj_ready`"

# Cliente BigQuery autenticado com o projeto
client = bigquery.Client(project=PROJECT_ID)

# ================================================================================
# PERGUNTAS DA ANÁLISE EXPLORATÓRIA
# ================================================================================
# 1. Média de mortalidade por acidente de moto e motoneta no município do RJ
# 2. Evolução do número de veículos por ano
# 3. Taxa de motos por população
# 4. Quantidade de acidentados por motocicleta e motoneta por ano
# 5. Local de ocorrência do óbito

# ================================================================================
# ETAPA 1 — CARREGAMENTO DOS DADOS
# ================================================================================

# Carrega a tabela de frota de veículos
sql_frota = f"""
SELECT *
FROM {VW_FROTA}
"""

# Carrega a tabela de mortalidade (todos os óbitos do município)
sql_mortalidade = f"""
SELECT *
FROM {VW_MORTALIDADE}
"""

# Carrega a tabela de população do município
sql_populacao = f"""
SELECT *
FROM {VW_POPULACAO}
"""

df_frota = client.query(sql_frota, location="US").to_dataframe()
df_mortalidade = client.query(sql_mortalidade, location="US").to_dataframe()
df_populacao = client.query(sql_populacao, location="US").to_dataframe()

# ================================================================================
# ETAPA 2 — EXPLORAÇÃO INICIAL DAS TABELAS
# ================================================================================

# Visualiza as primeiras linhas de cada tabela
print("Frota:")
print(df_frota.head())
print()

print("Mortalidade:")
print(df_mortalidade.head())
print()

print("População:")
print(df_populacao.head())

# Verifica tipos de dados e valores nulos
print(df_frota.info())
print(df_mortalidade.info())
print(df_populacao.info())

# Lista as colunas disponíveis em cada tabela
print(df_frota.columns)
print(df_mortalidade.columns)
print(df_populacao.columns)

# Verifica o período coberto por cada tabela
print("Frota:")
print(df_frota["ano"].min(), df_frota["ano"].max())

print("\nMortalidade:")
print(df_mortalidade["ano"].min(), df_mortalidade["ano"].max())

print("\nPopulação:")
print(df_populacao["ano"].min(), df_populacao["ano"].max())

# Distribuição de registros por ano na tabela de frota
print(df_frota["ano"].value_counts().sort_index())

# Distribuição das causas de óbito por capítulo do CID-10
print(
    df_mortalidade["causa_basica_descricao_capitulo"]
    .value_counts()
    .head(10)
)

# Amostra dos códigos de causa básica presentes nos dados
print(
    df_mortalidade["causa_basica"].head(20).tolist()
)

# ================================================================================
# ETAPA 3 — FILTRO DE ÓBITOS POR ACIDENTE DE MOTO (CID V20–V29)
# ================================================================================
# Os códigos CID V20 a V29 correspondem a acidentes de transporte
# envolvendo motocicletas e motonetas

sql_causa = f"""
SELECT
    ano,
    id_municipio_ocorrencia,
    causa_basica,
    idade,
    sexo,
    local_ocorrencia
FROM {VW_MORTALIDADE}
WHERE sigla_uf = 'RJ'
    AND id_municipio_ocorrencia = '3304557'
    AND SUBSTR(causa_basica, 1, 1) = 'V'
    AND SAFE_CAST(SUBSTR(causa_basica, 2, 2) AS INT64) BETWEEN 20 AND 29
    AND ano BETWEEN 2003 AND 2024
    AND id_municipio_ocorrencia IS NOT NULL
"""

df_causa = client.query(sql_causa, location="US").to_dataframe()

print(df_causa.head())
print(f"\nTotal de óbitos: {len(df_causa):,}")
print("\nÓbitos por ano:")
print(df_causa["ano"].value_counts().sort_index())

# Distribuição por código CID específico
print(
    df_causa["causa_basica"]
    .value_counts()
    .sort_values(ascending=False)
)

# ================================================================================
# ETAPA 4 — CÁLCULO DA FROTA MÉDIA ANUAL
# ================================================================================
# Filtra apenas motocicletas e motonetas e calcula a média mensal por ano

frota_motos = df_frota[
    df_frota["tipo_veiculo"].isin(["motocicleta", "motoneta"])
]

frota_anual = (
    frota_motos
    .groupby("ano")["quantidade"]
    .mean()
    .reset_index(name="frota_media")
)

print(frota_anual)

# ================================================================================
# ETAPA 5 — ANÁLISE ANUAL: ÓBITOS x FROTA
# ================================================================================
# Conta óbitos por ano e cruza com a frota média

analise_anual = (
    df_causa
    .groupby("ano")
    .size()
    .reset_index(name="obitos")
)

# Join entre óbitos e frota pelo ano
analise_anual = analise_anual.merge(
    frota_anual,
    on="ano",
    how="inner"
)

print(analise_anual)

# Coluna derivada: taxa de óbitos por 10 mil motos
analise_anual["obitos_por_10mil_motos"] = (
    analise_anual["obitos"]
    / analise_anual["frota_media"]
) * 10000

print(analise_anual)

# ================================================================================
# ETAPA 6 — POPULAÇÃO TOTAL POR ANO
# ================================================================================

populacao_anual = (
    df_populacao
    .groupby("ano")["populacao"]
    .sum()
    .reset_index(name="populacao_total")
)
print(populacao_anual)

# ================================================================================
# ETAPA 7 — DISTRIBUIÇÕES POR PERFIL DA VÍTIMA
# ================================================================================

# Distribuição de óbitos por faixa etária
mortalidade_idade = (
    df_causa
    .groupby("idade").size()
    .reset_index(name="total_obitos")
)
print(mortalidade_idade)

# Distribuição de óbitos por sexo
mortalidade_sexo = (
    df_causa
    .groupby("sexo").size()
    .reset_index(name="total_obitos")
)
print(mortalidade_sexo)

# Distribuição de óbitos por local de ocorrência
local_mortalidade = (
    df_causa
    .groupby("local_ocorrencia").size()
    .reset_index(name="total_obitos")
)
print(local_mortalidade)

# ================================================================================
# ETAPA 8 — EXPORTAÇÃO DAS TABELAS PARA O BIGQUERY
# ================================================================================
# As tabelas são salvas no BigQuery para uso no dashboard do Looker Studio

analise_anual.to_gbq(f"{DATASET}.tb_analise_anual", project_id=PROJECT_ID, if_exists="replace")
mortalidade_idade.to_gbq(f"{DATASET}.tb_mortalidade_idade", project_id=PROJECT_ID, if_exists="replace")
mortalidade_sexo.to_gbq(f"{DATASET}.tb_mortalidade_sexo", project_id=PROJECT_ID, if_exists="replace")
local_mortalidade.to_gbq(f"{DATASET}.tb_local_mortalidade", project_id=PROJECT_ID, if_exists="replace")

# ================================================================================
# ETAPA 9 — VISUALIZAÇÕES
# ================================================================================

# Gráfico 1: Evolução da taxa de óbitos por 10 mil motos ao longo dos anos
plt.figure(figsize=(12, 5))
plt.plot(analise_anual["ano"], analise_anual["obitos_por_10mil_motos"])
plt.title("Óbitos por 10 Mil Motos")
plt.xlabel("ano")
plt.ylabel("obitos_por_10mil_motos")
plt.show()

# Gráfico 2: Distribuição de óbitos por idade
plt.figure(figsize=(10, 6))
plt.bar(mortalidade_idade["idade"], mortalidade_idade["total_obitos"])
plt.title('Mortalidade de Moto por Idade')
plt.xlabel("Idade")
plt.ylabel("Quantidade de Óbitos")
plt.xticks(rotation=0)
plt.show()

# Gráfico 3: Comparativo de óbitos por sexo
plt.figure(figsize=(10, 6))
plt.bar(mortalidade_sexo["sexo"], mortalidade_sexo["total_obitos"])
plt.title("Mortalidade de Moto por Sexo")
plt.xlabel("Sexo")
plt.ylabel("Quantidade de Óbitos")
plt.xticks(rotation=0)
plt.show()

# Gráfico 4: Evolução da frota de motos ao longo dos anos
plt.figure(figsize=(12, 5))
plt.plot(analise_anual["ano"], analise_anual["frota_media"])
plt.title("Evolução de Frota por Ano")
plt.xlabel("ano")
plt.ylabel("frota_media")
plt.show()

# Gráfico 5: Distribuição de óbitos por local de ocorrência
plt.figure(figsize=(10, 6))
plt.bar(local_mortalidade["local_ocorrencia"], local_mortalidade["total_obitos"])
plt.title("Local de ocorrência do óbito")
plt.xlabel("Local de Ocorrência")
plt.ylabel("Quantidade de Óbitos")
plt.xticks(rotation=0)
plt.show()