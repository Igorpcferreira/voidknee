#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilador VoidKnee -> C
----------------------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Union
import re
import argparse
import sys
import subprocess


# Mapeamentos de tipos e formatos 


TYPE_MAP: Dict[str, str] = {
    "inteirao": "int",
    "flutuante": "float",
    "dobradura": "double",
}

PRINTF_FMT: Dict[str, str] = {
    "int": "%d",
    "float": "%f",
    "double": "%lf",   
}

SCANF_FMT: Dict[str, str] = {
    "int": "%d",
    "float": "%f",
    "double": "%lf",
}


# Léxico (Tokens)

KEYWORDS = {
    "inteirao": "TIPO_INTEIRAO",
    "flutuante": "TIPO_FLUTUANTE",
    "dobradura": "TIPO_DOBRADURA",
    "sejoelho": "SE",
    "outracoisa": "SENAO",
    "praCada": "PARA",
    "enquantoDoi": "ENQUANTO",
    "mostraAi": "MOSTRA",
    "entradaAi": "ENTRADA",
    "verdadeiro": "VERDADEIRO",
    "falso": "FALSO",
}

TOKEN_REGEX_PARTS = [
    # ordem importa: tokens "longos" primeiro
    ("TRICOMMENT", r"///[^\n]*"),                 # preservado em AST
    ("COMMENT",    r"//[^\n]*"),                  # ignorado
    ("WHITESPACE", r"[ \t\r\n]+"),                # ignorado
    ("LE",         r"<="),
    ("GE",         r">="),
    ("EQ",         r"=="),
    ("NE",         r"!="),
    ("AND",        r"&&"),
    ("OR",         r"\|\|"),
    ("ASSIGN",     r"="),
    ("LT",         r"<"),
    ("GT",         r">"),
    ("PLUS",       r"\+"),
    ("MINUS",      r"-"),
    ("MUL",        r"\*"),
    ("DIV",        r"/"),
    ("MOD",        r"%"),
    ("NOT",        r"!"),
    ("LPAREN",     r"\("),
    ("RPAREN",     r"\)"),
    ("LBRACE",     r"\{"),
    ("RBRACE",     r"\}"),
    ("SEMI",       r";"),
    ("COMMA",      r","),
    ("STRING",     r"\"(?:[^\"\\]|\\.)*\""),
    ("FLOAT",      r"\d+\.\d+(?:[eE][+-]?\d+)?"),
    ("INT",        r"\d+"),
    ("ID",         r"[A-Za-z_]\w*"),
]

MASTER_RE = re.compile("|".join(f"(?P<{name}>{regex})" for name, regex in TOKEN_REGEX_PARTS))

@dataclass
class Token:
    tipo: str
    lexema: Optional[str]
    pos: int

class AnalisadorLexico:
    def __init__(self, texto: str):
        self.texto = texto

    def tokenizar(self) -> List[Token]:
        tokens: List[Token] = []
        for mo in MASTER_RE.finditer(self.texto):
            tipo = mo.lastgroup
            lex = mo.group()
            pos = mo.start()

            if tipo in ("WHITESPACE", "COMMENT"):
                continue

            if tipo == "ID":
                k = KEYWORDS.get(lex)
                if k:
                    tokens.append(Token(k, lex, pos))
                else:
                    tokens.append(Token("ID", lex, pos))
                continue

            if tipo == "STRING":
                tokens.append(Token("STRING", lex, pos))
                continue

            if tipo in ("INT", "FLOAT"):
                tokens.append(Token(tipo, lex, pos))
                continue

            if tipo == "TRICOMMENT":
                # guardamos somente o texto após ///
                texto = lex[3:].strip()
                tokens.append(Token("COMENTARIO", texto, pos))
                continue

            tokens.append(Token(tipo, lex, pos))

        tokens.append(Token("EOF", None, len(self.texto)))
        return tokens


# AST (Nós)

# Declarações e comandos
@dataclass
class Programa:
    comandos: List["Comando"]

class Comando: ...
@dataclass
class Comentario(Comando):
    texto: str

@dataclass
class Bloco(Comando):
    comandos: List[Comando]

@dataclass
class DeclaracaoVar(Comando):
    tipo: str     # "int" | "float" | "double" 
    nome: str
    inicial: Optional["Expr"]

@dataclass
class Atribuicao(Comando):
    nome: str
    expr: "Expr"

@dataclass
class Se(Comando):
    cond: "Expr"
    entao: Bloco
    senao: Optional[Bloco]

@dataclass
class Enquanto(Comando):
    cond: "Expr"
    corpo: Bloco

@dataclass
class ParaCada(Comando):
    inicial: Optional[Comando]   # pode ser DeclaracaoVar ou Atribuicao ou None
    cond: Optional["Expr"]
    passo: Optional[Comando]     # geralmente Atribuicao ou expressão
    corpo: Bloco

@dataclass
class Mostra(Comando):
    expr: "Expr"  # suportará concatenação com +

@dataclass
class Entrada(Comando):
    nome: str

@dataclass
class ExpressaoStmt(Comando):
    expr: "Expr"

# Expressões
class Expr: ...
@dataclass
class LiteralNumero(Expr):
    valor: Union[int, float]
    eh_float: bool  # True se veio de FLOAT

@dataclass
class LiteralString(Expr):
    valor: str

@dataclass
class Variavel(Expr):
    nome: str

@dataclass
class Unario(Expr):
    op: str
    expr: Expr

@dataclass
class Binario(Expr):
    op: str
    esq: Expr
    dir: Expr

# Parser (descida recursiva)

class ErroSintatico(SyntaxError):
    pass

class AnalisadorSintatico:
    def __init__(self, tokens: List[Token]):
        self.toks = tokens
        self.i = 0

    def espiar(self) -> Token:
        return self.toks[self.i]

    def avancar(self) -> Token:
        t = self.toks[self.i]
        self.i += 1
        return t

    def combinar(self, *tipos: str) -> bool:
        if self.espiar().tipo in tipos:
            self.avancar()
            return True
        return False

    def consumir(self, tipo: str, msg: str) -> Token:
        if self.espiar().tipo == tipo:
            return self.avancar()
        t = self.espiar()
        raise ErroSintatico(f"{msg} na pos {t.pos}, obtido {t.tipo}")

    # ---- programa/declarações ----

    def analisar_programa(self) -> Programa:
        comandos: List[Comando] = []
        while self.espiar().tipo != "EOF":
            comandos.append(self.comando())
        return Programa(comandos)

    def comando(self) -> Comando:
        t = self.espiar().tipo

        if t in ("TIPO_INTEIRAO", "TIPO_FLUTUANTE", "TIPO_DOBRADURA"):
            return self.declaracao_var()

        if t == "MOSTRA":
            return self.comando_mostra()

        if t == "ENTRADA":
            return self.comando_entrada()

        if t == "SE":
            return self.comando_se()

        if t == "ENQUANTO":
            return self.comando_enquanto()

        if t == "PARA":
            return self.comando_para()

        if t == "LBRACE":
            return self.bloco()

        if t == "COMENTARIO":
            texto = self.avancar().lexema or ""
            # Comentário de linha "isolado" é um comando
            return Comentario(texto)

        # Atribuição ou expressão simples
        # lookahead: ID '=' expr ';'
        if t == "ID":
            if self.toks[self.i + 1].tipo == "ASSIGN":
                return self.atribuicao_stmt()
            # senão, tratamos como expressão-; (chamada no futuro)
        # expressão solta (usada no passo do for, etc.)
        expr = self.expressao()
        self.consumir("SEMI", "Esperado ';' após expressão")
        return ExpressaoStmt(expr)

    def bloco(self) -> Bloco:
        self.consumir("LBRACE", "Esperado '{'")
        comandos: List[Comando] = []
        while self.espiar().tipo != "RBRACE":
            comandos.append(self.comando())
        self.consumir("RBRACE", "Esperado '}'")
        return Bloco(comandos)

    def declaracao_var(self) -> DeclaracaoVar:
        tipo_tok = self.avancar()  # já sabemos que é um TIPO_*
        tipo_c = {
            "TIPO_INTEIRAO": "int",
            "TIPO_FLUTUANTE": "float",
            "TIPO_DOBRADURA": "double",
        }[tipo_tok.tipo]

        nome = self.consumir("ID", "Esperado identificador").lexema  # type: ignore
        inicial: Optional[Expr] = None
        if self.combinar("ASSIGN"):
            inicial = self.expressao()
        self.consumir("SEMI", "Esperado ';' após declaração")
        return DeclaracaoVar(tipo_c, nome, inicial)

    def atribuicao_stmt(self) -> Atribuicao:
        nome = self.consumir("ID", "Esperado identificador").lexema  # type: ignore
        self.consumir("ASSIGN", "Esperado '='")
        expr = self.expressao()
        self.consumir("SEMI", "Esperado ';' após atribuição")
        return Atribuicao(nome, expr)

    def comando_mostra(self) -> Mostra:
        self.consumir("MOSTRA", "Esperado 'mostraAi'")
        self.consumir("LPAREN", "Esperado '('")
        expr = self.expressao()  # suporta concatenação com '+'
        self.consumir("RPAREN", "Esperado ')'")
        self.consumir("SEMI", "Esperado ';' após mostraAi(...)")
        return Mostra(expr)

    def comando_entrada(self) -> Entrada:
        self.consumir("ENTRADA", "Esperado 'entradaAi'")
        self.consumir("LPAREN", "Esperado '('")
        nome = self.consumir("ID", "Esperado identificador em entradaAi(...)").lexema  # type: ignore
        self.consumir("RPAREN", "Esperado ')'")
        self.consumir("SEMI", "Esperado ';' após entradaAi(...)")
        return Entrada(nome)

    def comando_se(self) -> Se:
        self.consumir("SE", "Esperado 'sejoelho'")
        self.consumir("LPAREN", "Esperado '('")
        cond = self.expressao()
        self.consumir("RPAREN", "Esperado ')'")
        entao = self.bloco()
        senao = None
        if self.combinar("SENAO"):
            senao = self.bloco()
        return Se(cond, entao, senao)

    def comando_enquanto(self) -> Enquanto:
        self.consumir("ENQUANTO", "Esperado 'enquantoDoi'")
        self.consumir("LPAREN", "Esperado '('")
        cond = self.expressao()
        self.consumir("RPAREN", "Esperado ')'")
        corpo = self.bloco()
        return Enquanto(cond, corpo)

    def comando_para(self) -> ParaCada:
        self.consumir("PARA", "Esperado 'praCada'")
        self.consumir("LPAREN", "Esperado '('")

        # parte inicial pode ser declaração, atribuição ou vazia
        inicial: Optional[Comando] = None
        if self.espiar().tipo in ("TIPO_INTEIRAO", "TIPO_FLUTUANTE", "TIPO_DOBRADURA"):
            inicial = self.declaracao_var()
        elif self.espiar().tipo != "SEMI":
            # tente expressão/atribuição e consuma ';'
            if self.espiar().tipo == "ID" and self.toks[self.i + 1].tipo == "ASSIGN":
                inicial = self.atribuicao_stmt()
            else:
                expr = self.expressao()
                self.consumir("SEMI", "Esperado ';' na parte inicial do praCada")
                inicial = ExpressaoStmt(expr)
        else:
            self.consumir("SEMI", "Esperado ';' na parte inicial do praCada")

        # condição 
        cond: Optional[Expr] = None
        if self.espiar().tipo != "SEMI":
            cond = self.expressao()
        self.consumir("SEMI", "Esperado ';' após condição do praCada")

        # passo ( até )
        passo: Optional[Comando] = None
        if self.espiar().tipo != "RPAREN":
            # aceitar atribuição ou expressão
            if self.espiar().tipo == "ID" and self.toks[self.i + 1].tipo == "ASSIGN":
                nome = self.avancar().lexema  # type: ignore
                self.consumir("ASSIGN", "Esperado '=' no passo do praCada")
                expr = self.expressao()
                passo = Atribuicao(nome, expr)
            else:
                expr = self.expressao()
                passo = ExpressaoStmt(expr)

        self.consumir("RPAREN", "Esperado ')'")
        corpo = self.bloco()
        return ParaCada(inicial, cond, passo, corpo)

    # ---- expressões ----
    # assignment -> logical_or ( '=' assignment )?
    def expressao(self) -> Expr:
        expr = self.logical_or()
        if self.combinar("ASSIGN"):
            # tratamos '=' aqui, mas só permitiremos se a esquerda for Variavel quando usado (semântico)
            direito = self.expressao()
            return Binario("=", expr, direito)
        return expr

    def logical_or(self) -> Expr:
        expr = self.logical_and()
        while self.combinar("OR"):
            direito = self.logical_and()
            expr = Binario("||", expr, direito)
        return expr

    def logical_and(self) -> Expr:
        expr = self.igualdade()
        while self.combinar("AND"):
            direito = self.igualdade()
            expr = Binario("&&", expr, direito)
        return expr

    def igualdade(self) -> Expr:
        expr = self.comparacao()
        while True:
            if self.combinar("EQ"):
                expr = Binario("==", expr, self.comparacao())
            elif self.combinar("NE"):
                expr = Binario("!=", expr, self.comparacao())
            else:
                break
        return expr

    def comparacao(self) -> Expr:
        expr = self.termo()
        while True:
            if self.combinar("LT"):
                expr = Binario("<", expr, self.termo())
            elif self.combinar("LE"):
                expr = Binario("<=", expr, self.termo())
            elif self.combinar("GT"):
                expr = Binario(">", expr, self.termo())
            elif self.combinar("GE"):
                expr = Binario(">=", expr, self.termo())
            else:
                break
        return expr

    def termo(self) -> Expr:
        expr = self.fator()
        while True:
            if self.combinar("PLUS"):
                expr = Binario("+", expr, self.fator())
            elif self.combinar("MINUS"):
                expr = Binario("-", expr, self.fator())
            else:
                break
        return expr

    def fator(self) -> Expr:
        expr = self.unario()
        while True:
            if self.combinar("MUL"):
                expr = Binario("*", expr, self.unario())
            elif self.combinar("DIV"):
                expr = Binario("/", expr, self.unario())
            elif self.combinar("MOD"):
                expr = Binario("%", expr, self.unario())
            else:
                break
        return expr

    def unario(self) -> Expr:
        if self.combinar("NOT"):
            return Unario("!", self.unario())
        if self.combinar("MINUS"):
            return Unario("-", self.unario())
        return self.primario()

    def primario(self) -> Expr:
        tok = self.espiar()

        if self.combinar("INT"):
            return LiteralNumero(int(tok.lexema), False)  # type: ignore

        if self.combinar("FLOAT"):
            return LiteralNumero(float(tok.lexema), True)  # type: ignore

        if self.combinar("VERDADEIRO"):
            return LiteralNumero(1, False)
        if self.combinar("FALSO"):
            return LiteralNumero(0, False)

        if self.combinar("STRING"):
            # remover aspas externas mantendo escapes
            texto = tok.lexema[1:-1] if tok.lexema is not None else ""  # type: ignore
            return LiteralString(texto)

        if self.combinar("ID"):
            return Variavel(tok.lexema or "")

        if self.combinar("LPAREN"):
            expr = self.expressao()
            self.consumir("RPAREN", "Esperado ')'")
            return expr

        raise ErroSintatico(f"Token inesperado {tok.tipo} na pos {tok.pos}")

# Semântica

class ErroSemantico(Exception):
    pass

class AnalisadorSemantico:
    def __init__(self):
        self.tabela: Dict[str, str] = {}  # nome -> tipo C ("int"/"float"/"double")

    def analisar(self, prog: Programa) -> None:
        for cmd in prog.comandos:
            self._verificar_cmd(cmd)

    # ajuda para inferir tipos em expressões (simplificado)
    def _tipo_expr(self, e: Expr) -> str:
        if isinstance(e, LiteralNumero):
            return "double" if e.eh_float else "int"
        if isinstance(e, LiteralString):
            return "string"
        if isinstance(e, Variavel):
            if e.nome not in self.tabela:
                raise ErroSemantico(f"Variável '{e.nome}' usada antes da declaração")
            return self.tabela[e.nome]
        if isinstance(e, Unario):
            return self._tipo_expr(e.expr)
        if isinstance(e, Binario):
            if e.op == "=":
                # atribuição como expressão (usada em praCada passo). lhs deve ser Variavel.
                if not isinstance(e.esq, Variavel):
                    raise ErroSemantico("Atribuição requer variável à esquerda")
                tdir = self._tipo_expr(e.dir)
                # pro nosso caso, aceitamos promoções simples (int->float->double)
                return self.tabela.get(e.esq.nome, tdir)
            # demais operadores: se houver string, vira string (para +), mas só aceitaremos em Mostra
            tesq = self._tipo_expr(e.esq)
            tdir = self._tipo_expr(e.dir)
            if e.op == "+" and ("string" in (tesq, tdir)):
                return "string"
            # numérico: domina o maior
            ordem = {"int": 0, "float": 1, "double": 2}
            if tesq not in ordem or tdir not in ordem:
                # algo não-numérico em contexto numérico
                return "int"
            return ["int", "float", "double"][max(ordem[tesq], ordem[tdir])]
        raise ErroSemantico(f"Expressão desconhecida: {e}")

    def _verificar_cmd(self, cmd: Comando) -> None:
        if isinstance(cmd, Comentario):
            return
        if isinstance(cmd, Bloco):
            for c in cmd.comandos:
                self._verificar_cmd(c)
            return
        if isinstance(cmd, DeclaracaoVar):
            if cmd.nome in self.tabela:
                raise ErroSemantico(f"Variável '{cmd.nome}' redeclarada")
            self.tabela[cmd.nome] = cmd.tipo
            if cmd.inicial is not None:
                self._tipo_expr(cmd.inicial)  # apenas força visita
            return
        if isinstance(cmd, Atribuicao):
            if cmd.nome not in self.tabela:
                raise ErroSemantico(f"Variável '{cmd.nome}' não declarada")
            self._tipo_expr(cmd.expr)
            return
        if isinstance(cmd, Mostra):
            # Permitir string/numérico + concatenações
            self._tipo_expr(cmd.expr)
            return
        if isinstance(cmd, Entrada):
            if cmd.nome not in self.tabela:
                raise ErroSemantico(f"Variável '{cmd.nome}' não declarada (entradaAi)")
            return
        if isinstance(cmd, Se):
            self._tipo_expr(cmd.cond)
            for c in cmd.entao.comandos:
                self._verificar_cmd(c)
            if cmd.senao:
                for c in cmd.senao.comandos:
                    self._verificar_cmd(c)
            return
        if isinstance(cmd, Enquanto):
            self._tipo_expr(cmd.cond)
            for c in cmd.corpo.comandos:
                self._verificar_cmd(c)
            return
        if isinstance(cmd, ParaCada):
            if cmd.inicial:
                self._verificar_cmd(cmd.inicial)
            if cmd.cond:
                self._tipo_expr(cmd.cond)
            if cmd.passo:
                self._verificar_cmd(cmd.passo)
            for c in cmd.corpo.comandos:
                self._verificar_cmd(c)
            return
        if isinstance(cmd, ExpressaoStmt):
            self._tipo_expr(cmd.expr)
            return
        raise ErroSemantico(f"Comando desconhecido: {cmd}")

# Gerador de Código C

class GeradorCodigo:
    def __init__(self, prog: Programa, sem: AnalisadorSemantico):
        self.prog = prog
        self.sem = sem
        self.linhas: List[str] = []

    def gerar(self) -> str:
        self.linhas = ["#include <stdio.h>", "", "int main(void) {"]

        # declarações no topo (padrão didático)
        for nome, tipo in self.sem.tabela.items():
            self.linhas.append(f"    {tipo} {nome};")

        # comandos do programa
        for cmd in self.prog.comandos:
            self._emit_cmd(cmd, indent=1)

        self.linhas.append("    return 0;")
        self.linhas.append("}")
        return "\n".join(self.linhas)

    # ----- helpers -----

    def _indent(self, n: int) -> str:
        return "    " * n

    def _emit_cmd(self, cmd: Comando, indent: int) -> None:
        if isinstance(cmd, Comentario):
            self.linhas.append(self._indent(indent) + f"/* {cmd.texto} */")
            return

        if isinstance(cmd, DeclaracaoVar):
            # já declaramos no topo; aqui só inicialização (se houver)
            if cmd.inicial is not None:
                self.linhas.append(self._indent(indent) + f"{cmd.nome} = {self._emit_expr(cmd.inicial)};")
            return

        if isinstance(cmd, Atribuicao):
            self.linhas.append(self._indent(indent) + f"{cmd.nome} = {self._emit_expr(cmd.expr)};")
            return

        if isinstance(cmd, ExpressaoStmt):
            self.linhas.append(self._indent(indent) + f"{self._emit_expr(cmd.expr)};")
            return

        if isinstance(cmd, Mostra):
            fmt, args = self._montar_printf(cmd.expr)
            if args:
                self.linhas.append(self._indent(indent) + f'printf("{fmt}", {", ".join(args)});')
            else:
                self.linhas.append(self._indent(indent) + f'printf("{fmt}");')
            return

        if isinstance(cmd, Entrada):
            tipo = self.sem.tabela.get(cmd.nome, "int")
            spec = SCANF_FMT.get(tipo, "%d")
            self.linhas.append(self._indent(indent) + f'scanf("{spec}", &{cmd.nome});')
            return

        if isinstance(cmd, Se):
            self.linhas.append(self._indent(indent) + f"if ({self._emit_expr(cmd.cond)}) "+"{")
            for c in cmd.entao.comandos:
                self._emit_cmd(c, indent+1)
            self.linhas.append(self._indent(indent) + "}")
            if cmd.senao:
                self.linhas.append(self._indent(indent) + "else {")
                for c in cmd.senao.comandos:
                    self._emit_cmd(c, indent+1)
                self.linhas.append(self._indent(indent) + "}")
            return

        if isinstance(cmd, Enquanto):
            self.linhas.append(self._indent(indent) + f"while ({self._emit_expr(cmd.cond)}) "+"{")
            for c in cmd.corpo.comandos:
                self._emit_cmd(c, indent+1)
            self.linhas.append(self._indent(indent) + "}")
            return

        if isinstance(cmd, ParaCada):
            # construir as 3 partes do for
            p1 = ""
            if isinstance(cmd.inicial, DeclaracaoVar):
                # declarar no topo: então somente inicialização
                if cmd.inicial.inicial is not None:
                    p1 = f"{cmd.inicial.nome} = {self._emit_expr(cmd.inicial.inicial)}"
            elif isinstance(cmd.inicial, Atribuicao):
                p1 = f"{cmd.inicial.nome} = {self._emit_expr(cmd.inicial.expr)}"
            elif isinstance(cmd.inicial, ExpressaoStmt):
                p1 = f"{self._emit_expr(cmd.inicial.expr)}"
            # condição
            p2 = self._emit_expr(cmd.cond) if cmd.cond else ""
            # passo
            if isinstance(cmd.passo, Atribuicao):
                p3 = f"{cmd.passo.nome} = {self._emit_expr(cmd.passo.expr)}"
            elif isinstance(cmd.passo, ExpressaoStmt):
                p3 = f"{self._emit_expr(cmd.passo.expr)}"
            else:
                p3 = ""

            self.linhas.append(self._indent(indent) + f"for ({p1}; {p2}; {p3}) "+"{")
            for c in cmd.corpo.comandos:
                self._emit_cmd(c, indent+1)
            self.linhas.append(self._indent(indent) + "}")
            return

        raise RuntimeError(f"Comando não suportado no gerador: {cmd}")

    # construir printf com concatenação de strings e expressões
    def _montar_printf(self, expr: Expr) -> Tuple[str, List[str]]:
        partes = self._flatten_concat(expr)
        fmt_parts: List[str] = []
        args: List[str] = []

        for p in partes:
            if isinstance(p, str):
                fmt_parts.append(p)
            else:
                tipo = self._inferir_tipo_expr(p)
                spec = PRINTF_FMT.get(tipo, "%g")
                fmt_parts.append(spec)
                args.append(self._emit_expr(p))

        return "".join(fmt_parts), args

    def _flatten_concat(self, expr: Expr) -> List[Union[str, Expr]]:
        # quebra uma árvore de + em lista de partes (strings e exprs)
        if isinstance(expr, Binario) and expr.op == "+":
            return self._flatten_concat(expr.esq) + self._flatten_concat(expr.dir)
        if isinstance(expr, LiteralString):
            return [expr.valor]
        return [expr]

    def _inferir_tipo_expr(self, e: Expr) -> str:
        # simples: alinhar com analisador
        if isinstance(e, LiteralNumero):
            return "double" if e.eh_float else "int"
        if isinstance(e, Variavel):
            return self.sem.tabela.get(e.nome, "int")
        # heurística: se contém float/double em filhos => double, senão int
        if isinstance(e, Binario):
            te = self._inferir_tipo_expr(e.esq)
            td = self._inferir_tipo_expr(e.dir)
            ordem = {"int": 0, "float": 1, "double": 2}
            return ["int", "float", "double"][max(ordem.get(te,0), ordem.get(td,0))]
        if isinstance(e, Unario):
            return self._inferir_tipo_expr(e.expr)
        return "int"

    def _emit_expr(self, e: Expr) -> str:
        if isinstance(e, LiteralNumero):
            return str(e.valor)
        if isinstance(e, LiteralString):
            # colocar de volta aspas
            # OBS: em printf, strings literais vão direto no formato. Aqui só ocorre fora do mostraAi.
            return '"' + e.valor.replace('"', r'\"') + '"'
        if isinstance(e, Variavel):
            return e.nome
        if isinstance(e, Unario):
            return f"({e.op}{self._emit_expr(e.expr)})"
        if isinstance(e, Binario):
            if e.op == "=":
                # permitir atribuição como expressão
                if isinstance(e.esq, Variavel):
                    return f"({e.esq.nome} = {self._emit_expr(e.dir)})"
            return f"({self._emit_expr(e.esq)} {e.op} {self._emit_expr(e.dir)})"
        raise RuntimeError(f"Expressão não suportada: {e}")

# Pipeline: Tokens -> Parser -> AST -> Semântica -> Código C

def traduzir(codigo_fonte: str) -> str:
    lexico = AnalisadorLexico(codigo_fonte)
    tokens = lexico.tokenizar()

    parser = AnalisadorSintatico(tokens)
    prog = parser.analisar_programa()

    sem = AnalisadorSemantico()
    sem.analisar(prog)

    gerador = GeradorCodigo(prog, sem)
    return gerador.gerar()

# Execução do C gerado (opcional) – preservado do seu fluxo

def executar_codigo_c(codigo_c: str, nome_arquivo: str = "saida.c"):
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(codigo_c)
    subprocess.run(["gcc", nome_arquivo, "-o", "saida_exec"], check=True)
    resultado = subprocess.run(["./saida_exec"], capture_output=True, text=True)
    print("\\n=== Saída do programa em C ===")
    print(resultado.stdout)

# CLI

def main():
    parser_arg = argparse.ArgumentParser(description="Compilador (Tokens->Parser->AST->CodeGen) VoidKnee -> C")
    parser_arg.add_argument("arquivo_entrada", nargs="?", help="Arquivo .vk (VoidKnee). Se ausente, lê da stdin.")
    parser_arg.add_argument("-o", "--arquivo_saida", help="Arquivo .c de saída (padrão: stdout)")
    parser_arg.add_argument("--run", action="store_true", help="Compila e executa o C gerado")
    args = parser_arg.parse_args()

    if args.arquivo_entrada:
        with open(args.arquivo_entrada, "r", encoding="utf-8") as arq:
            fonte = arq.read()
    else:
        fonte = sys.stdin.read()

    codigo_c = traduzir(fonte)

    if args.arquivo_saida:
        with open(args.arquivo_saida, "w", encoding="utf-8") as arq:
            arq.write(codigo_c)
    else:
        print("=== Código C gerado ===")
        print(codigo_c)

    if args.run:
        executar_codigo_c(codigo_c)

if __name__ == "__main__":
    main()
