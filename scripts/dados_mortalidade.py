from google.cloud import bigquery
import os
import sys
import pandas as pd


# ================================================================================
# CONFIGURAÇÕES DO PROJETO
# ================================================================================

# ID do projeto no Google Cloud / BigQuery
PROJECT_ID = "projetofinalebac-505021"

# Dataset onde estão as views e onde será criada a tabela final
DATASET = "dados_mortalidade"

# Nome da view que já existe no BigQuery
SOURCE_TABLE_NAME = "vw_mortalidade_motociclistas_rj"

# Nome da tabela final que será criada pelo Python
READY_TABLE_NAME = "vw_mortalidade_motociclistas_rj_ready"


# Monta os nomes completos das tabelas
SOURCE_TABLE = f"`{PROJECT_ID}.{DATASET}.{SOURCE_TABLE_NAME}`"
TABLE = f"`{PROJECT_ID}.{DATASET}.{READY_TABLE_NAME}`"


# Região do BigQuery.
# None permite que o BigQuery utilize a localização padrão.
DATASET_LOCATION = None


# Cria o cliente para conexão com o BigQuery
client = bigquery.Client(project=PROJECT_ID)


# ================================================================================
# FUNÇÃO PARA EXECUTAR QUERIES
# ================================================================================

def run_query(query: str):
    """
    Executa uma query no BigQuery.

    A função centraliza a execução das consultas para evitar
    repetir o código de conexão em cada etapa.
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

# Consulta algumas linhas da view para verificar se:
# - a conexão está funcionando;
# - a view existe;
# - os nomes das colunas estão corretos;
# - os dados estão sendo retornados.

sql_preview = f"""
SELECT
    ano,
    sigla_uf,
    sigla_uf_nome,
    causa_basica,
    causa_basica_descricao_subcategoria,
    causa_basica_descricao_categoria,
    causa_basica_descricao_capitulo,
    data_obito,
    idade,
    sexo,
    estado_civil,
    ocupacao,
    local_ocorrencia,
    id_municipio_ocorrencia,
    municipio_nome,
    tipo_obito_ocorrencia,
    tipo_morte_ocorrencia
FROM {SOURCE_TABLE}
LIMIT 10
"""

print("SQL preview:")

try:

    # Executa a consulta e transforma o resultado em DataFrame
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
# 2.1 - Óbitos por tipo de morte e local de ocorrência
# ------------------------------------------------------------------------------

# Agrupa os registros pelo tipo de morte e pelo local onde ocorreu.
# COUNT(*) conta quantos registros existem em cada combinação.

sql_mt = f"""
SELECT
    tipo_morte_ocorrencia,
    local_ocorrencia,
    COUNT(*) AS total
FROM {SOURCE_TABLE}
GROUP BY
    tipo_morte_ocorrencia,
    local_ocorrencia
ORDER BY total DESC
"""

try:

    df_mt = run_query(sql_mt).to_dataframe()

    print("Distribuição por tipo de morte e local de ocorrência:")
    print(df_mt.to_string(index=False))
    print()

except Exception as e:

    print(f"✗ Erro na análise de tipo de morte: {e}")
    sys.exit(1)


# ------------------------------------------------------------------------------
# 2.2 - Óbitos em via pública por sexo
# ------------------------------------------------------------------------------

# Filtra apenas os registros cuja ocorrência foi em via pública
# e depois agrupa os resultados por sexo.

sql_lo = f"""
SELECT
    sexo,
    COUNT(*) AS total
FROM {SOURCE_TABLE}
WHERE LOWER(local_ocorrencia) = 'via publica'
GROUP BY sexo
ORDER BY total DESC
"""

try:

    df_lo = run_query(sql_lo).to_dataframe()

    print("Óbitos em via pública por sexo:")
    print(df_lo.to_string(index=False))
    print()

except Exception as e:

    print(f"✗ Erro na análise de local de ocorrência: {e}")
    sys.exit(1)


# ------------------------------------------------------------------------------
# 2.3 - Causas básicas relacionadas a motociclistas
# ------------------------------------------------------------------------------

# Os códigos V20 até V29 da CID-10 estão relacionados a acidentes
# envolvendo motociclistas.
#
# SUBSTR(causa_basica, 1, 1) = 'V'
# verifica se o código começa com V.
#
# SAFE_CAST(SUBSTR(causa_basica, 2, 2) AS INT64)
# transforma os dois números seguintes em número inteiro.
#
# BETWEEN 20 AND 29
# mantém apenas os códigos V20 até V29.

sql_cb = f"""
SELECT
    causa_basica,
    causa_basica_descricao_subcategoria,
    sexo,
    idade,
    local_ocorrencia,
    ano
FROM {SOURCE_TABLE}
WHERE SUBSTR(causa_basica, 1, 1) = 'V'
  AND SAFE_CAST(SUBSTR(causa_basica, 2, 2) AS INT64) BETWEEN 20 AND 29
  AND ano IN (2023, 2024, 2025, 2026)
LIMIT 100
"""

try:

    df_cb = run_query(sql_cb).to_dataframe()

    print("Causas relacionadas a acidentes com motociclistas:")
    print(df_cb.to_string(index=False))
    print()

except Exception as e:

    print(f"✗ Erro na análise de causa básica: {e}")
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

    COUNTIF(sigla_uf IS NULL) AS sigla_nulo,

    COUNTIF(causa_basica IS NULL) AS causa_nulo,

    COUNTIF(data_obito IS NULL) AS data_obito_nulo,

    COUNTIF(idade IS NULL) AS idade_nulo,

    COUNTIF(sexo IS NULL) AS sexo_nulo,

    COUNTIF(estado_civil IS NULL) AS estado_nulo,

    COUNTIF(ocupacao IS NULL) AS ocupacao_nulo,

    COUNTIF(local_ocorrencia IS NULL) AS ocorrencia_nulo,

    COUNTIF(id_municipio_ocorrencia IS NULL) AS id_municipio_nulo,

    COUNTIF(tipo_obito_ocorrencia IS NULL) AS tipo_obito_nulo,

    COUNTIF(tipo_morte_ocorrencia IS NULL) AS tipo_morte_nulo,

    COUNT(DISTINCT CONCAT(
        COALESCE(CAST(ano AS STRING), ''),
        COALESCE(sigla_uf, ''),
        COALESCE(causa_basica, ''),
        COALESCE(CAST(data_obito AS STRING), ''),
        COALESCE(CAST(idade AS STRING), ''),
        COALESCE(sexo, ''),
        COALESCE(estado_civil, ''),
        COALESCE(ocupacao, ''),
        COALESCE(local_ocorrencia, ''),
        COALESCE(CAST(id_municipio_ocorrencia AS STRING), ''),
        COALESCE(tipo_obito_ocorrencia, ''),
        COALESCE(tipo_morte_ocorrencia, '')
    )) AS registros_distintos

FROM {SOURCE_TABLE}
"""


try:

    # Executa a consulta de validação
    val_result = run_query(sql_validacao).to_dataframe()


    # Recupera os valores retornados pelo BigQuery
    total = val_result["total"].values[0]

    ano_nulo = val_result["ano_nulo"].values[0]
    sigla_nulo = val_result["sigla_nulo"].values[0]
    causa_nulo = val_result["causa_nulo"].values[0]
    data_obito_nulo = val_result["data_obito_nulo"].values[0]
    idade_nulo = val_result["idade_nulo"].values[0]
    sexo_nulo = val_result["sexo_nulo"].values[0]
    estado_nulo = val_result["estado_nulo"].values[0]
    ocupacao_nulo = val_result["ocupacao_nulo"].values[0]
    ocorrencia_nulo = val_result["ocorrencia_nulo"].values[0]
    id_municipio_nulo = val_result["id_municipio_nulo"].values[0]
    tipo_obito_nulo = val_result["tipo_obito_nulo"].values[0]
    tipo_morte_nulo = val_result["tipo_morte_nulo"].values[0]


    # Exibe o resultado da validação
    print(f"Total de registros: {total:,}")
    print()

    print(f"Valores nulos em ano: {ano_nulo}")
    print(f"Valores nulos em sigla_uf: {sigla_nulo}")
    print(f"Valores nulos em causa_basica: {causa_nulo}")
    print(f"Valores nulos em data_obito: {data_obito_nulo}")
    print(f"Valores nulos em idade: {idade_nulo}")
    print(f"Valores nulos em sexo: {sexo_nulo}")
    print(f"Valores nulos em estado_civil: {estado_nulo}")
    print(f"Valores nulos em ocupacao: {ocupacao_nulo}")
    print(f"Valores nulos em local_ocorrencia: {ocorrencia_nulo}")
    print(f"Valores nulos em id_municipio_ocorrencia: {id_municipio_nulo}")
    print(f"Valores nulos em tipo_obito_ocorrencia: {tipo_obito_nulo}")
    print(f"Valores nulos em tipo_morte_ocorrencia: {tipo_morte_nulo}")
    print()


    # Soma a quantidade de valores nulos encontrados.
    # Se o resultado for zero, nenhum dos campos analisados possui NULL.

    total_nulos = (
        ano_nulo
        + sigla_nulo
        + causa_nulo
        + data_obito_nulo
        + idade_nulo
        + sexo_nulo
        + estado_nulo
        + ocupacao_nulo
        + ocorrencia_nulo
        + id_municipio_nulo
        + tipo_obito_nulo
        + tipo_morte_nulo
    )


    if total_nulos == 0:

        print("✓ Dados VÁLIDOS: sem valores nulos")

    else:

        print("⚠ Atenção: existem valores nulos")

    print()


except Exception as e:

    print(f"✗ Erro na validação: {e}")


# ================================================================================
# ETAPA 4 - GARANTIR QUE O DATASET EXISTE
# ================================================================================

print("=" * 80)
print("ETAPA 4 - ESTRUTURANDO TABELA PRÓPRIA")
print("=" * 80)


# Define o endereço do dataset
dataset_ref = f"{PROJECT_ID}.{DATASET}"


try:

    # Verifica se o dataset já existe
    client.get_dataset(dataset_ref)

    print(f"✓ Dataset já existe: {dataset_ref}")


except Exception:

    # Caso não exista, cria o dataset
    dataset = bigquery.Dataset(dataset_ref)

    if DATASET_LOCATION:
        dataset.location = DATASET_LOCATION

    client.create_dataset(dataset)

    print(f"✓ Dataset criado: {dataset_ref}")


# ================================================================================
# ETAPA 5 - CRIAR TABELA FINAL
# ================================================================================

print()
print("Criando tabela final...")


# CREATE OR REPLACE TABLE:
#
# cria a tabela caso ela não exista;
# substitui a tabela caso ela já exista.
#
# Aqui também fazemos uma seleção dos campos que serão mantidos
# na tabela final e garantimos os tipos de ano e idade.

sql_create_table = f"""
CREATE OR REPLACE TABLE {TABLE} AS

SELECT
    CAST(ano AS INT64) AS ano,
    sigla_uf,
    sigla_uf_nome,
    causa_basica,
    causa_basica_descricao_subcategoria,
    causa_basica_descricao_categoria,
    causa_basica_descricao_capitulo,
    data_obito,
    CAST(idade AS INT64) AS idade,
    sexo,
    estado_civil,
    ocupacao,
    local_ocorrencia,
    id_municipio_ocorrencia,
    municipio_nome,
    tipo_obito_ocorrencia,
    tipo_morte_ocorrencia

FROM {SOURCE_TABLE}

WHERE ano IS NOT NULL
  AND sigla_uf IS NOT NULL
  AND causa_basica IS NOT NULL
  AND data_obito IS NOT NULL
  AND idade IS NOT NULL
  AND sexo IS NOT NULL
  AND local_ocorrencia IS NOT NULL
  AND id_municipio_ocorrencia IS NOT NULL
"""


print(sql_create_table)


try:

    # Executa a criação da tabela
    job = run_query(sql_create_table)

    # Aguarda o processamento terminar
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


    # Exibe o schema da tabela
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