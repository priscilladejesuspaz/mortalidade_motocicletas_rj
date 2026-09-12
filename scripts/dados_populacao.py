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
SOURCE_TABLE_NAME = "vw_populacao_rj"

# Nome da tabela final que será criada
READY_TABLE_NAME = "vw_populacao_rj_ready"

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
    id_municipio,
    sexo,
    grupo_idade,
    populacao
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
# 2.1 - População do município por ano
# ------------------------------------------------------------------------------

# O código 3304557 corresponde ao município do Rio de Janeiro.
#
# Aqui verificamos os registros populacionais dos anos analisados.

sql_ano = f"""
SELECT
    ano,
    id_municipio,
    sexo,
    grupo_idade,
    populacao
FROM {SOURCE_TABLE}
WHERE ano IN (2023, 2024, 2025, 2026)
  AND id_municipio = "3304557"
LIMIT 10
"""

try:

    df_ano = run_query(sql_ano).to_dataframe()

    print("População do município do Rio de Janeiro:")
    print(df_ano.to_string(index=False))
    print()

except Exception as e:

    print(f"✗ Erro na análise por ano: {e}")
    sys.exit(1)


# ------------------------------------------------------------------------------
# 2.2 - População por ano, sexo e grupo de idade
# ------------------------------------------------------------------------------

# SUM(populacao) soma a população.
#
# GROUP BY separa os resultados por:
# - ano;
# - município;
# - sexo;
# - grupo de idade.
#
# Isso permite analisar a composição demográfica
# do município ao longo dos anos.

sql_municipio = f"""
SELECT
    ano,
    id_municipio,
    sexo,
    grupo_idade,
    SUM(populacao) AS total_populacao
FROM {SOURCE_TABLE}
WHERE ano IN (2023, 2024, 2025, 2026)
  AND id_municipio = "3304557"
GROUP BY
    ano,
    id_municipio,
    sexo,
    grupo_idade
ORDER BY ano DESC
LIMIT 10
"""

print("SQL análise populacional:")
print(sql_municipio)

try:

    df_municipio = run_query(sql_municipio).to_dataframe()

    print("População por ano, sexo e grupo de idade:")
    print(df_municipio.to_string(index=False))
    print()

except Exception as e:

    print(f"✗ Erro na análise populacional: {e}")
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

    COUNTIF(id_municipio IS NULL) AS id_nulo,

    COUNTIF(sexo IS NULL) AS sexo_nulo,

    COUNTIF(grupo_idade IS NULL) AS idade_nulo,

    COUNTIF(populacao IS NULL) AS populacao_nulo,

    COUNT(DISTINCT CONCAT(
        COALESCE(CAST(ano AS STRING), ""),
        COALESCE(CAST(id_municipio AS STRING), ""),
        COALESCE(sexo, ""),
        COALESCE(grupo_idade, ""),
        COALESCE(CAST(populacao AS STRING), "")
    )) AS registros_distintos

FROM {SOURCE_TABLE}
"""

print(sql_validacao)

try:

    val_result = run_query(sql_validacao).to_dataframe()

    # Recupera os resultados da validação
    total = val_result["total"].values[0]

    ano_nulo = val_result["ano_nulo"].values[0]
    id_nulo = val_result["id_nulo"].values[0]
    sexo_nulo = val_result["sexo_nulo"].values[0]
    idade_nulo = val_result["idade_nulo"].values[0]
    populacao_nulo = val_result["populacao_nulo"].values[0]

    print()
    print(f"Total de registros: {total:,}")
    print()

    print(f"Valores nulos em ano: {ano_nulo}")
    print(f"Valores nulos em id_municipio: {id_nulo}")
    print(f"Valores nulos em sexo: {sexo_nulo}")
    print(f"Valores nulos em grupo_idade: {idade_nulo}")
    print(f"Valores nulos em populacao: {populacao_nulo}")
    print()

    # Verifica se existem valores nulos nos campos analisados
    if (
        ano_nulo == 0
        and id_nulo == 0
        and sexo_nulo == 0
        and idade_nulo == 0
        and populacao_nulo == 0
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
    id_municipio,
    sexo,
    grupo_idade,
    populacao,
    CAST(ano AS INT64) AS ano

FROM {SOURCE_TABLE}

WHERE ano IS NOT NULL
  AND id_municipio IS NOT NULL
  AND sexo IS NOT NULL
  AND grupo_idade IS NOT NULL
  AND populacao IS NOT NULL

ORDER BY
    ano,
    populacao
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
    print("✓ Tabela criada com sucesso:")
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