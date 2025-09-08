#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tradutor VoidKnee -> C
-------------------------------------------------
Autor: Igor Ferreira, Luiz Sabino, Victor Alcanfor e Rafael Marques
Objetivo: traduzir programas escritos na nossa linguagem
de brinquedo **VoidKnee** (cheia de joelhos doloridos 🦵😅)
para C.

O tradutor cobre:
- Tipos: inteirao, flutuante, dobradura
- Estruturas de controle: sejoelho, outracoisa, praCada, enquantoDoi
- Entrada e saída: entradaAi (scanf), mostraAi (printf)
- Suporte a concatenação com '+', estilo "Vida: " + vida

Observações importantes:
- Ainda é limitado: não suporta funções, arrays, operadores lógicos avançados etc.
- Comentários que começam com `///` no VoidKnee viram comentários em C (`/* ... */`).
"""

import re
from typing import Dict, List

# ---------------------------------------------------------
# Mapeamento básico da VoidKnee -> C
# ---------------------------------------------------------

# Tipos de dados
TYPE_MAP = {
    "inteirao": "int",
    "flutuante": "float",
    "dobradura": "double",
}

# Estruturas de controle
CTRL_MAP = {
    "sejoelho": "if",
    "outracoisa": "else",
    "praCada": "for",
    "enquantoDoi": "while",
}

# Formatos usados em printf e scanf
PRINTF_FMT = {
    "int": "%d",
    "float": "%f",
    "double": "%lf",
}

SCANF_FMT = {
    "int": "%d",
    "float": "%f",
    "double": "%lf",
}

# Regex pra identificar variáveis (nome válido)
IDENT_RE = r"[A-Za-z_]\w*"

# ---------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------

def _strip_comments(linha_codigo: str) -> str:
    """
    Remove comentários estilo // (mas não mexe dentro de strings).
    Assim conseguimos analisar as linhas limpas.
    """
    caracteres_processados = []
    dentro_de_string = False
    indice_atual = 0

    while indice_atual < len(linha_codigo):
        caractere = linha_codigo[indice_atual]

        # Detecta início/fim de string
        if caractere == '"' and (indice_atual == 0 or linha_codigo[indice_atual - 1] != '\\'):
            dentro_de_string = not dentro_de_string
            caracteres_processados.append(caractere)
            indice_atual += 1
            continue

        # Se encontrar // fora de string, ignora o resto da linha
        if not dentro_de_string and caractere == '/' and indice_atual + 1 < len(linha_codigo) and linha_codigo[indice_atual + 1] == '/':
            break  

        caracteres_processados.append(caractere)
        indice_atual += 1

    return "".join(caracteres_processados)

def build_symbol_table(codigo_fonte: str) -> dict[str, str]:
    """
    Cria uma tabela com as variáveis declaradas em VoidKnee
    e seus respectivos tipos em C.

    Exemplo:
    inteirao x = 0; -> {"x": "int"}
    flutuante y; -> {"y": "float"}
    """
    tabela_simbolos: dict[str, str] = {}
    expressao_declaracao = re.compile(
        rf"\b({'|'.join(TYPE_MAP.keys())})\b\s+({IDENT_RE})(?:\s*=[^;]*)?;"
    )

    for linha_original in codigo_fonte.splitlines():
        linha_sem_comentario = _strip_comments(linha_original).strip()
        correspondencia_declaracao = expressao_declaracao.search(linha_sem_comentario)
        if correspondencia_declaracao:
            tipo_voidknee, nome_variavel = correspondencia_declaracao.group(1), correspondencia_declaracao.group(2)
            tipo_c = TYPE_MAP[tipo_voidknee]
            tabela_simbolos[nome_variavel] = tipo_c
    return tabela_simbolos


def replace_keywords(linha_codigo: str) -> str:
    """
    Substitui as palavras-chave da VoidKnee pelas do C.
    Exemplo:
    sejoelho -> if
    inteirao -> int
    """

    def replace_outside_strings(texto: str, mapa_substituicao: Dict[str, str]) -> str:
        """
        Substitui palavras-chave somente quando estão fora de strings.
        Exemplo: não deve mudar nada dentro de "aspas".
        """
        def substituir_palavra(correspondencia_regex):
            palavra = correspondencia_regex.group(0)
            return mapa_substituicao.get(palavra, palavra)

        padrao_regex = r"\b(" + "|".join(re.escape(chave) for chave in mapa_substituicao.keys()) + r")\b"
        caracteres_processados = []
        dentro_de_string = False
        indice_atual = 0

        while indice_atual < len(texto):
            caractere = texto[indice_atual]

            if caractere == '"' and (indice_atual == 0 or texto[indice_atual - 1] != '\\'):
                dentro_de_string = not dentro_de_string
                caracteres_processados.append(caractere)
                indice_atual += 1
                continue

            if not dentro_de_string:
                texto_restante = texto[indice_atual:]
                substituido = re.sub(padrao_regex, substituir_palavra, texto_restante)
                caracteres_processados.append(substituido)
                break
            else:
                caracteres_processados.append(caractere)
                indice_atual += 1

        return "".join(caracteres_processados)

    # Primeiro substitui tipos, depois estruturas de controle
    linha_codigo = replace_outside_strings(linha_codigo, TYPE_MAP)
    linha_codigo = replace_outside_strings(linha_codigo, CTRL_MAP)
    return linha_codigo


# ---------------------------------------------------------
# Tradução de mostraAi e entradaAi
# ---------------------------------------------------------

def parse_mostraAi_arguments(argumentos_texto: str, tabela_simbolos: Dict[str, str]) -> str:
    """
    Converte os argumentos do mostraAi para um printf.
    
    Exemplo em VoidKnee:
    mostraAi("Vida: " + vida + ", X: " + x);
    
    Vira em C:
    printf("Vida: %d, X: %d", vida, x);
    """
    partes_expressao: List[str] = []
    buffer_caracteres = []
    dentro_de_string = False
    indice_atual = 0

    # Divide em partes separadas pelo operador +
    while indice_atual < len(argumentos_texto):
        caractere = argumentos_texto[indice_atual]
        if caractere == '"' and (indice_atual == 0 or argumentos_texto[indice_atual - 1] != '\\'):
            dentro_de_string = not dentro_de_string
            buffer_caracteres.append(caractere)
            indice_atual += 1
            continue
        if not dentro_de_string and caractere == '+':
            partes_expressao.append("".join(buffer_caracteres).strip())
            buffer_caracteres = []
            indice_atual += 1
            continue
        buffer_caracteres.append(caractere)
        indice_atual += 1

    if buffer_caracteres:
        partes_expressao.append("".join(buffer_caracteres).strip())

    lista_formatos = []
    lista_argumentos = []

    # Monta a string de formatação e os argumentos
    for parte in partes_expressao:
        parte = parte.strip()
        if not parte:
            continue
        if parte.startswith('"') and parte.endswith('"'):
            lista_formatos.append(parte[1:-1])  # literal de string
        else:
            if re.fullmatch(IDENT_RE, parte) and parte in tabela_simbolos:
                tipo_c = tabela_simbolos[parte]
                lista_formatos.append(PRINTF_FMT.get(tipo_c, "%s"))
                lista_argumentos.append(parte)
            else:
                lista_formatos.append("%g")
                lista_argumentos.append(parte)

    string_formatacao = '"' + "".join(lista_formatos) + '"'
    if lista_argumentos:
        return f'printf({string_formatacao}, {", ".join(lista_argumentos)});'
    else:
        return f'printf({string_formatacao});'


def translate_io(linha_codigo: str, tabela_simbolos: Dict[str, str]) -> str:
    """
    Faz a mágica das funções de IO:
    - mostraAi(...) -> printf(...)
    - entradaAi(x) -> scanf("%d", &x);
    """
    # Tradução do mostraAi
    correspondencia_saida = re.search(r"\bmostraAi\b\s*\((.*)\)\s*;", linha_codigo)
    if correspondencia_saida:
        conteudo_interno = correspondencia_saida.group(1).strip()
        saida_c = parse_mostraAi_arguments(conteudo_interno, tabela_simbolos)
        return re.sub(r"\bmostraAi\b\s*\(.*\)\s*;", saida_c, linha_codigo)

    # Tradução do entradaAi
    correspondencia_entrada = re.search(r"\bentradaAi\b\s*\(\s*(" + IDENT_RE + r")\s*\)\s*;", linha_codigo)
    if correspondencia_entrada:
        nome_variavel = correspondencia_entrada.group(1)
        tipo_c = tabela_simbolos.get(nome_variavel, None)
        formato_c = SCANF_FMT.get(tipo_c or "", "%d")
        entrada_c = f'scanf("{formato_c}", &{nome_variavel});'
        return re.sub(r"\bentradaAi\b\s*\(.*\)\s*;", entrada_c, linha_codigo)

    return linha_codigo

# ---------------------------------------------------------
# Função principal de tradução
# ---------------------------------------------------------

def translate(codigo_fonte: str) -> str:
    """
    Traduz um programa completo escrito em VoidKnee para C.
    Faz a substituição de palavras-chave, tratamento de IO,
    indentação e comentários.
    """
    linhas_codigo = codigo_fonte.splitlines()
    tabela_simbolos = build_symbol_table(codigo_fonte)

    saida_c = ["#include <stdio.h>", "", "int main(void) {"]

    nivel_indentacao = 1
    for linha_original in linhas_codigo:
        linha_sem_quebra = linha_original.rstrip("\n")

        # Comentários estilo /// viram /* ... */
        if linha_sem_quebra.strip().startswith("///"):
            comentario = linha_sem_quebra.strip()[3:].strip()
            linha_convertida = ("    " * nivel_indentacao) + f"/* {comentario} */"
            saida_c.append(linha_convertida)
            continue

        linha_limpa = _strip_comments(linha_sem_quebra).strip()
        if not linha_limpa:
            saida_c.append("")
            continue

        # Ajusta indentação ao fechar chaves
        quantidade_fechamentos = linha_limpa.count("}")
        if quantidade_fechamentos:
            nivel_indentacao = max(1, nivel_indentacao - quantidade_fechamentos)

        # Substitui palavras-chave e traduz IO
        linha_traduzida = replace_keywords(linha_limpa)
        linha_traduzida = translate_io(linha_traduzida, tabela_simbolos)

        # Garante ; no final, quando necessário
        linha_traduzida_podada = linha_traduzida.strip()
        if (not linha_traduzida_podada.endswith(";")
                and not linha_traduzida_podada.endswith("{")
                and not linha_traduzida_podada.endswith("}")):
            linha_traduzida += ";"

        saida_c.append(("    " * nivel_indentacao) + linha_traduzida)

        # Abre chaves -> aumenta indentação
        quantidade_aberturas = linha_limpa.count("{")
        if quantidade_aberturas:
            nivel_indentacao += quantidade_aberturas

    saida_c.append("    return 0;")
    saida_c.append("}")
    return "\n".join(saida_c)

# ---------------------------------------------------------
# Execução do código C traduzido
# ---------------------------------------------------------

import subprocess

def executar_codigo_c(codigo_c: str, nome_arquivo: str = "saida.c"):
    """
    Salva o código em C, compila com gcc e executa o binário gerado.
    """
    # 1. Salvar código em um arquivo .c
    with open(nome_arquivo, "w", encoding="utf-8") as arquivo_c:
        arquivo_c.write(codigo_c)

    # 2. Compilar com gcc -> gera "saida_exec"
    subprocess.run(["gcc", nome_arquivo, "-o", "saida_exec"], check=True)

    # 3. Executar o programa compilado
    resultado = subprocess.run(["./saida_exec"], capture_output=True, text=True)

    print("\n=== Saída do programa em C ===")
    print(resultado.stdout)

# ---------------------------------------------------------
# Ponto de entrada (main)
# ---------------------------------------------------------

def main():
    """
    Interpreta os argumentos de linha de comando para rodar o tradutor.
    Exemplo de uso:
        python voidknee_translator.py exemplo_voidknee.vk -o exemplo_traduzido.c
    """
    import argparse, sys

    parser_argumentos = argparse.ArgumentParser(description="Tradutor VoidKnee -> C")
    parser_argumentos.add_argument("arquivo_entrada", nargs="?", help="Arquivo .vk (VoidKnee). Se ausente, lê da entrada padrão.")
    parser_argumentos.add_argument("-o", "--arquivo_saida", help="Arquivo .c de saída (padrão: stdout)")
    parser_argumentos.add_argument("--run", action="store_true", help="Compila e executa o código C gerado")
    argumentos_recebidos = parser_argumentos.parse_args()

    # Lê o código-fonte
    codigo_fonte = ""
    if argumentos_recebidos.arquivo_entrada:
        with open(argumentos_recebidos.arquivo_entrada, "r", encoding="utf-8") as arquivo:
            codigo_fonte = arquivo.read()
    else:
        codigo_fonte = sys.stdin.read()

    # Traduz
    codigo_traduzido = translate(codigo_fonte)

    # Salva no arquivo de saída (ou mostra no console)
    if argumentos_recebidos.arquivo_saida:
        with open(argumentos_recebidos.arquivo_saida, "w", encoding="utf-8") as arquivo:
            arquivo.write(codigo_traduzido)
    else:
        print("=== Código C traduzido ===")
        print(codigo_traduzido)

    # Se a flag --run foi passada, compila e executa o C
    if argumentos_recebidos.run:
        executar_codigo_c(codigo_traduzido)