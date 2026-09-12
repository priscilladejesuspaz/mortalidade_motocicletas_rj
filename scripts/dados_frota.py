from google.cloud import bigquery
import pandas as pd
import os
import sys
from pathlib import Path


# ================================================================================
# CONFIGURAÇÕES DO PROJETO
# ================================================================================

# ID do projeto no Google Cloud / BigQuery
PROJECT_ID = "projetofinalebac-505021"

# Dataset onde estão as views e onde será criada a tabela final
DATASET = "dados_mortalidade"

# Nome da view que já existe no BigQuery
SOURCE_TABLE_NAME = "vw_frota_motos_rj"

# Nome da tabela final que será criada
READY_TABLE_NAME = "vw_frota_motos_rj_ready"

# Referência completa da view de origem
SOURCE_TABLE = f"`{PROJECT_ID}.{DATASET}.{SOURCE_TABLE_NAME}`"

# Referência completa da tabela final
TABLE = f"`{PROJECT_ID}.{DATASET}.{READY_TABLE_NAME}`"

# Região do dataset no BigQuery
DATASET_LOCATION = "US"


# ================================================================================
# CONEXÃO COM O BIGQUERY
# ================================================================================

# Cria o cliente para conexão com o BigQuery
client = bigquery.Client(project=PROJECT_ID)


def run_query(query: str):
    """
    Executa uma query no BigQuery respeitando
    a localização definida para o dataset.
    """

    if DATASET_LOCATION:
        return client.query(query, location=DATASET_LOCATION)

    return client.query(query)


# ================================================================================
# ETAPA 1 - PREVIEW DOS DADOS
# ================================================================================

print("=" * 80)
print("ETAPA 1 - PREVIEW DOS DADOS")
print("=" * 80)

# Consulta algumas linhas da view para verificar:
# - conexão com o BigQuery;
# - existência da view;
# - nomes das colunas;
# - estrutura dos dados.

sql_preview = f"""
SELECT
    ano,
    mes,
    sigla_uf,
    id_municipio,
    tipo_veiculo,
    quantidade
FROM {SOURCE_TABLE}
LIMIT 10
"""

print("SQL preview:")
print(sql_preview)

try:

    df_preview = run_query(sql_preview).to_dataframe()

    print(df_preview.to_string(index=False))
    print()

except Exception as e:

    print(f"✗ Erro no preview: {e}")
    sys.exit(1)


# ================================================================================
# ETAPA 2 - ANÁLISES EXPLORATÓRIAS
# ================================================================================

print("=" * 80)
print("ETAPA 2 - ANÁLISES EXPLORATÓRIAS")
print("=" * 80)


# ------------------------------------------------------------------------------
# 2.1 - Tipos de veículos analisados
# ------------------------------------------------------------------------------

# Filtra motocicletas e motonetas nos anos selecionados.
# O objetivo é verificar a distribuição dos registros
# utilizados na análise.

sql_tipo = f"""
SELECT
    ano,
    sigla_uf,
    id_municipio,
    tipo_veiculo
FROM {SOURCE_TABLE}
WHERE tipo_veiculo IN ("motocicleta", "motoneta")
  AND ano IN (2023, 2024, 2025, 2026)
  AND sigla_uf = "RJ"
LIMIT 100
"""

try:

    df_tipo = run_query(sql_tipo).to_dataframe()

    print("Tipos de veículos:")
    print(df_tipo.to_string(index=False))
    print()

except Exception as e:

    print(f"✗ Erro na análise de tipos de veículos: {e}")
    sys.exit(1)


# ------------------------------------------------------------------------------
# 2.2 - Frota de motocicletas e motonetas no município do Rio de Janeiro
# ------------------------------------------------------------------------------

# O código 3304557 corresponde ao município do Rio de Janeiro.
#
# Aqui verificamos os registros de motocicletas e motonetas
# associados ao município.

sql_codigo = f"""
SELECT
    quantidade,
    id_municipio,
    sigla_uf,
    tipo_veiculo
FROM {SOURCE_TABLE}
WHERE id_municipio = "3304557"
  AND sigla_uf = "RJ"
  AND tipo_veiculo IN ("motoneta", "motocicleta")
LIMIT 100
"""

try:

    df_codigo = run_query(sql_codigo).to_dataframe()

    print("Frota de motocicletas e motonetas no município do Rio de Janeiro:")
    print(df_codigo.to_string(index=False))
    print()

except Exception as e:

    print(f"✗ Erro na análise por município: {e}")
    sys.exit(1)


# ------------------------------------------------------------------------------
# 2.3 - Total de veículos por ano e tipo
# ------------------------------------------------------------------------------

# SUM(quantidade) soma a quantidade de veículos.
#
# GROUP BY separa os resultados por:
# - ano;
# - tipo de veículo;
# - UF;
# - município.

sql_total = f"""
SELECT
    ano,
    tipo_veiculo,
    sigla_uf,
    id_municipio,
    SUM(quantidade) AS qtd_veiculo
FROM {SOURCE_TABLE}
WHERE tipo_veiculo IN ("motocicleta", "motoneta")
  AND sigla_uf = "RJ"
  AND ano IN (2023, 2024, 2025, 2026)
  AND id_municipio = "3304557"
GROUP BY
    ano,
    tipo_veiculo,
    sigla_uf,
    id_municipio
ORDER BY ano DESC
"""

try:

    df_total = run_query(sql_total).to_dataframe()

    print("Total de motocicletas e motonetas por ano:")
    print(df_total.to_string(index=False))
    print()

except Exception as e:

    print(f"✗ Erro no cálculo da frota: {e}")
    sys.exit(1)


# ================================================================================
# ETAPA 3 - VALIDAÇÃO DOS DADOS
# ================================================================================

print("=" * 80)
print("ETAPA 3 - VALIDAÇÃO DOS DADOS")
print("=" * 80)

# COUNT(*) calcula o total de registros.
#
# COUNTIF(condição) conta quantos registros atendem à condição.
#
# Exemplo:
#
# COUNTIF(ano IS NULL)
#
# significa:
# "quantos registros possuem ano nulo?"

sql_validacao = f"""
SELECT
    COUNT(*) AS total,

    COUNTIF(ano IS NULL) AS ano_nulo,

    COUNTIF(mes IS NULL) AS mes_nulo,

    COUNTIF(sigla_uf IS NULL) AS sigla_nulo,

    COUNTIF(id_municipio IS NULL) AS id_nulo,

    COUNTIF(tipo_veiculo IS NULL) AS tipo_nulo,

    COUNTIF(quantidade IS NULL) AS qtd_nulo,

    COUNT(DISTINCT CONCAT(
        COALESCE(CAST(ano AS STRING), ""),
        COALESCE(CAST(mes AS STRING), ""),
        COALESCE(sigla_uf, ""),
        COALESCE(CAST(id_municipio AS STRING), ""),
        COALESCE(tipo_veiculo, ""),
        COALESCE(CAST(quantidade AS STRING), "")
    )) AS registros_distintos

FROM {SOURCE_TABLE}
"""

print(sql_validacao)

try:

    val_result = run_query(sql_validacao).to_dataframe()

    # Recupera os resultados da validação
    total = val_result["total"].values[0]

    ano_nulo = val_result["ano_nulo"].values[0]
    mes_nulo = val_result["mes_nulo"].values[0]
    sigla_nulo = val_result["sigla_nulo"].values[0]
    id_nulo = val_result["id_nulo"].values[0]
    tipo_nulo = val_result["tipo_nulo"].values[0]
    qtd_nulo = val_result["qtd_nulo"].values[0]

    print()
    print(f"Total de registros: {total:,}")
    print()

    print(f"Valores nulos em ano: {ano_nulo}")
    print(f"Valores nulos em mes: {mes_nulo}")
    print(f"Valores nulos em sigla_uf: {sigla_nulo}")
    print(f"Valores nulos em id_municipio: {id_nulo}")
    print(f"Valores nulos em tipo_veiculo: {tipo_nulo}")
    print(f"Valores nulos em quantidade: {qtd_nulo}")
    print()

    # Verifica se existem valores nulos nos campos analisados
    if (
        ano_nulo == 0
        and mes_nulo == 0
        and sigla_nulo == 0
        and id_nulo == 0
        and tipo_nulo == 0
        and qtd_nulo == 0
    ):

        print("✓ Dados VÁLIDOS: sem valores nulos")

    else:

        print("⚠ Atenção: existem valores nulos")

    print()

except Exception as e:

    print(f"✗ Erro na validação: {e}")


# ================================================================================
# ETAPA 4 - CRIAR DATASET E TABELA PRÓPRIA NO PROJETO
# ================================================================================

print("=" * 80)
print("ETAPA 4 - ESTRUTURANDO TABELA PRÓPRIA")
print("=" * 80)

# Referência do dataset
dataset_ref = f"{PROJECT_ID}.{DATASET}"


# Verifica se o dataset já existe.
# Caso não exista, cria automaticamente.

try:

    client.get_dataset(dataset_ref)

    print(f"✓ Dataset já existe: {dataset_ref}")

except Exception:

    dataset = bigquery.Dataset(dataset_ref)

    # Define a localização do dataset
    dataset.location = DATASET_LOCATION

    client.create_dataset(dataset)

    print(f"✓ Dataset criado: {dataset_ref}")


# ================================================================================
# ETAPA 5 - CRIAR TABELA FINAL
# ================================================================================

print()
print("▶ Criando tabela final...")
print()


# CREATE OR REPLACE TABLE:
#
# - cria a tabela caso ela não exista;
# - substitui a tabela caso ela já exista.
#
# Os dados são selecionados da view de origem.
#
# CAST(ano AS INT64):
# garante que o campo ano seja armazenado como inteiro.
#
# O WHERE remove registros com campos essenciais nulos.

sql_create_table = f"""
CREATE OR REPLACE TABLE {TABLE} AS

SELECT
    mes,
    sigla_uf,
    id_municipio,
    tipo_veiculo,
    quantidade,
    CAST(ano AS INT64) AS ano

FROM {SOURCE_TABLE}

WHERE ano IS NOT NULL
  AND sigla_uf IS NOT NULL
  AND id_municipio IS NOT NULL
  AND tipo_veiculo IS NOT NULL
  AND quantidade IS NOT NULL

ORDER BY
    ano,
    sigla_uf
"""

print("SQL criação da tabela:")
print(sql_create_table)


try:

    # Executa a criação da tabela
    job = run_query(sql_create_table)

    # Aguarda a conclusão do processamento
    job.result()


    # Recupera informações da tabela criada
    table = client.get_table(
        f"{PROJECT_ID}.{DATASET}.{READY_TABLE_NAME}"
    )


    print()
    print(f"✓ Tabela criada com sucesso:")
    print(f"  {PROJECT_ID}.{DATASET}.{READY_TABLE_NAME}")

    print(f"✓ Total de linhas: {table.num_rows:,}")
    print(f"✓ Total de colunas: {len(table.schema)}")


    # Exibe o schema da tabela final
    print()
    print("Schema:")

    for field in table.schema:

        print(f"  - {field.name}: {field.field_type}")


    print()
    print("=" * 80)
    print("PROCESSO CONCLUÍDO")
    print("=" * 80)


except Exception as e:

    print(f"✗ Erro ao criar tabela: {e}")
    sys.exit(1)