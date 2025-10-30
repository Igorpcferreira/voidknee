
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilador VoidKnee -> C (V2.1)
----------------------------------------------------------------------------
Alterações desta versão (aplicadas sobre a V2):
  - Renomeação dos novos tipos para termos temáticos e descritivos:
      * verdadeQueDoi  -> boolean (mapeado para int 0/1 no C)
      * dorzinha       -> char (caractere único)
      * dorzona        -> char[] (string; declarar com tamanho: dorzona nome[30];)
  - Mantidas as demais funcionalidades: vetores/matrizes, if/loops, mostraAi/entradaAi,
    concatenação de strings, análise semântica e geração de C.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Union
import re
import argparse
import sys
import subprocess

# -----------------------------
#  Mapeamentos de tipos e C
# -----------------------------

# Tipos base aceitos pela linguagem (em C)
TYPE_MAP: Dict[str, str] = {
    "inteirao": "int",
    "flutuante": "float",
    "dobradura": "double",
    # Novos nomes (V2.1)
    "verdadeQueDoi": "int",   # booleano representado como int (0/1) em C
    "dorzinha": "char",       # caractere único
    "dorzona": "char",        # vetor de caracteres (string)
}

# Especificadores para printf por tipo base
PRINTF_FMT: Dict[str, str] = {
    "int": "%d",
    "float": "%f",
    "double": "%lf",
    "char": "%c",
    # char[] será tratado como %s dinamicamente
}

# Especificadores para scanf por tipo base
SCANF_FMT: Dict[str, str] = {
    "int": "%d",
    "float": "%f",
    "double": "%lf",
    "char": " %c",  # espaço inicial ignora newline anterior ao ler char isolado
    # char[] será tratado como %Ns com largura segura
}

# ------------------------------------
#  Léxico (Tokens) – compatível c/ V1
# ------------------------------------

KEYWORDS = {
    # tipos base (nomes "originais" + novos nomes da V2.1)
    "inteirao": "TIPO_INTEIRAO",
    "flutuante": "TIPO_FLUTUANTE",
    "dobradura": "TIPO_DOBRADURA",
    "verdadeQueDoi": "TIPO_BOOLEANO",
    "dorzinha": "TIPO_CHAR",
    "dorzona": "TIPO_CHAR",

    # controle/IO
    "sejoelho": "SE",
    "outracoisa": "SENAO",
    "praCada": "PARA",
    "enquantoDoi": "ENQUANTO",
    "mostraAi": "MOSTRA",
    "entradaAi": "ENTRADA",

    # booleanos literais
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
    ("LBRACKET",   r"\["),
    ("RBRACKET",   r"\]"),
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
                texto = lex[3:].strip()
                tokens.append(Token("COMENTARIO", texto, pos))
                continue

            tokens.append(Token(tipo, lex, pos))

        tokens.append(Token("EOF", None, len(self.texto)))
        return tokens

# ------------------
#  AST (Nós)
# ------------------

# Estruturas
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

# DeclaracaoVar agora suporta arrays (dims) e tipo_base
@dataclass
class DeclaracaoVar(Comando):
    tipo_base: str                # "int" | "float" | "double" | "char" (boolean => int)
    nome: str
    dims: List[int]               # [] escalar, [N] vetor, [M,N] matriz
    inicial: Optional["Expr"]

@dataclass
class Atribuicao(Comando):
    alvo: "LValue"                # variável ou acesso a array
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
    inicial: Optional[Comando]
    cond: Optional["Expr"]
    passo: Optional[Comando]
    corpo: Bloco

@dataclass
class Mostra(Comando):
    expr: "Expr"  # pode ser concatenação com +

@dataclass
class Entrada(Comando):
    alvo: "LValue"  # permite ler em var ou array element

@dataclass
class ExpressaoStmt(Comando):
    expr: "Expr"

# Expressões
class Expr: ...
class LValue(Expr): ...  # algo atribuível (var/acesso a array)

@dataclass
class LiteralNumero(Expr):
    valor: Union[int, float]
    eh_float: bool  # True se veio de FLOAT

@dataclass
class LiteralString(Expr):
    valor: str

@dataclass
class Variavel(LValue):
    nome: str

@dataclass
class AcessoArray(LValue):
    nome: str
    indices: List[Expr]  # 1D ou 2D

@dataclass
class Unario(Expr):
    op: str
    expr: Expr

@dataclass
class Binario(Expr):
    op: str
    esq: Expr
    dir: Expr

# ------------------
#  Parser (V2.1)
# ------------------

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

    def analisar_programa(self) -> Programa:
        comandos: List[Comando] = []
        while self.espiar().tipo != "EOF":
            comandos.append(self.comando())
        return Programa(comandos)

    def comando(self) -> Comando:
        t = self.espiar().tipo

        if t in ("TIPO_INTEIRAO", "TIPO_FLUTUANTE", "TIPO_DOBRADURA", "TIPO_BOOLEANO", "TIPO_CHAR"):
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
            return Comentario(texto)

        # Atribuição ou expressão simples
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

    def _mapear_tipo(self, tipo_tok: Token) -> str:
        return {
            "TIPO_INTEIRAO": "int",
            "TIPO_FLUTUANTE": "float",
            "TIPO_DOBRADURA": "double",
            "TIPO_BOOLEANO": "int",  # verdadeQueDoi => int (0/1)
            "TIPO_CHAR": "char",     # dorzinha/dorzona => char (char[] se com [])
        }[tipo_tok.tipo]

    def declaracao_var(self) -> DeclaracaoVar:
        tipo_tok = self.avancar()
        tipo_c = self._mapear_tipo(tipo_tok)

        nome = self.consumir("ID", "Esperado identificador").lexema  # type: ignore

        # Suporte a vetores/matrizes: nome[INT][INT]...
        dims: List[int] = []
        while self.combinar("LBRACKET"):
            tam = int(self.consumir("INT", "Esperado tamanho inteiro na dimensão do array").lexema)  # type: ignore
            self.consumir("RBRACKET", "Esperado ']' após tamanho")
            dims.append(tam)

        inicial: Optional[Expr] = None
        if self.combinar("ASSIGN"):
            inicial = self.expressao()

        self.consumir("SEMI", "Esperado ';' após declaração")
        return DeclaracaoVar(tipo_c, nome, dims, inicial)

    def atribuicao_stmt(self, alvo: LValue) -> Atribuicao:
        self.consumir("ASSIGN", "Esperado '='")
        expr = self.expressao()
        self.consumir("SEMI", "Esperado ';' após atribuição")
        return Atribuicao(alvo, expr)
    
    def atribuicao_expr(self, alvo: LValue) -> Atribuicao:
        self.consumir("ASSIGN", "Esperado '='")
        expr = self.expressao()
        # NÃO consome ';' aqui
        return Atribuicao(alvo, expr)

    def comando_mostra(self) -> Mostra:
        self.consumir("MOSTRA", "Esperado 'mostraAi'")
        self.consumir("LPAREN", "Esperado '('")

        exprs: List[Expr] = [self.expressao()]
        while self.combinar("COMMA"):  # múltiplos args
            exprs.append(self.expressao())

        self.consumir("RPAREN", "Esperado ')'")
        self.consumir("SEMI", "Esperado ';' após mostraAi(...)")

        return Mostra(exprs if len(exprs) > 1 else exprs[0])

    def comando_entrada(self) -> Entrada:
        self.consumir("ENTRADA", "Esperado 'entradaAi'")
        self.consumir("LPAREN", "Esperado '('")
        alvo = self._lvalue()
        self.consumir("RPAREN", "Esperado ')'")
        self.consumir("SEMI", "Esperado ';' após entradaAi(...)")
        return Entrada(alvo)

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

        # parte inicial: declaração, atribuição, expressão ou vazia
        inicial: Optional[Comando] = None
        if self.espiar().tipo in ("TIPO_INTEIRAO", "TIPO_FLUTUANTE", "TIPO_DOBRADURA", "TIPO_BOOLEANO", "TIPO_CHAR"):
            inicial = self.declaracao_var()
        elif self.espiar().tipo != "SEMI":
            alvo = self._lvalue()
            if self.espiar().tipo == "ASSIGN":
                inicial = self.atribuicao_stmt(alvo)
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

        # passo
        passo: Optional[Comando] = None
        if self.espiar().tipo == "ASSIGN":
            passo = self.atribuicao_expr(alvo)  # <-- sem consumir ';'
        else:
            expr = self.expressao()
            passo = ExpressaoStmt(expr)

        self.consumir("RPAREN", "Esperado ')'")
        corpo = self.bloco()
        return ParaCada(inicial, cond, passo, corpo)

    # ------------------
    #  Expressões
    # ------------------

    def expressao(self) -> Expr:
        return self.logical_or()

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

    def _lvalue(self) -> LValue:
        # lvalue := ID ('[' expr ']')*
        tok = self.consumir("ID", "Esperado identificador")
        nome = tok.lexema or ""
        indices: List[Expr] = []
        while self.combinar("LBRACKET"):
            idx_expr = self.expressao()
            self.consumir("RBRACKET", "Esperado ']' após índice")
            indices.append(idx_expr)
        if indices:
            return AcessoArray(nome, indices)
        return Variavel(nome)

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
            texto = tok.lexema[1:-1] if tok.lexema is not None else ""  # type: ignore
            return LiteralString(texto)

        if self.espiar().tipo == "ID":
            # pode ser var/acesso array ou atribuição na expressão
            lval = self._lvalue()
            if self.combinar("ASSIGN"):
                direito = self.expressao()
                return Binario("=", lval, direito)
            return lval

        if self.combinar("LPAREN"):
            expr = self.expressao()
            self.consumir("RPAREN", "Esperado ')'")
            return expr

        raise ErroSintatico(f"Token inesperado {tok.tipo} na pos {tok.pos}")

# ------------------
#  Semântica (V2.1)
# ------------------

class ErroSemantico(Exception):
    pass

@dataclass
class Simbolo:
    tipo_base: str        # "int"/"float"/"double"/"char"
    dims: List[int]       # [] escalar, [N], [M,N]

class AnalisadorSemantico:
    def __init__(self):
        self.tabela: Dict[str, Simbolo] = {}  # nome -> Simbolo

    def analisar(self, prog: Programa) -> None:
        for cmd in prog.comandos:
            self._verificar_cmd(cmd)

    # Inferência simplificada do tipo de uma expressão
    def _tipo_expr(self, e: Expr) -> str:
        if isinstance(e, LiteralNumero):
            return "double" if e.eh_float else "int"
        if isinstance(e, LiteralString):
            return "string"
        if isinstance(e, Variavel):
            simb = self._obter(e.nome)
            if len(simb.dims) > 0 and simb.tipo_base == "char":
                return "string"  # char[] tratado como string
            return simb.tipo_base
        if isinstance(e, AcessoArray):
            simb = self._obter(e.nome)
            if len(e.indices) > len(simb.dims):
                raise ErroSemantico("Índices excedem dimensões declaradas")
            if len(e.indices) == len(simb.dims):
                return simb.tipo_base
            return simb.tipo_base
        if isinstance(e, Unario):
            return self._tipo_expr(e.expr)
        if isinstance(e, Binario):
            if e.op == "=":
                if not isinstance(e.esq, LValue):
                    raise ErroSemantico("Atribuição requer alvo atribuível (variável/array)")
                tdir = self._tipo_expr(e.dir)
                return tdir
            # concatenação: se alguma parte for string → string
            tesq = self._tipo_expr(e.esq)
            tdir = self._tipo_expr(e.dir)
            if e.op == "+" and ("string" in (tesq, tdir)):
                return "string"
            # operações com boolean: tratamos como int
            ordem = {"int": 0, "float": 1, "double": 2, "char": 0}
            if tesq not in ordem or tdir not in ordem:
                return "int"
            return ["int", "float", "double"][max(ordem[tesq], ordem[tdir])]
        raise ErroSemantico(f"Expressão desconhecida: {e}")

    def _obter(self, nome: str) -> Simbolo:
        if nome not in self.tabela:
            raise ErroSemantico(f"Variável '{nome}' usada antes da declaração")
        return self.tabela[nome]

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
            self.tabela[cmd.nome] = Simbolo(cmd.tipo_base, cmd.dims)
            if cmd.inicial is not None:
                self._tipo_expr(cmd.inicial)  # força visita
            return
        if isinstance(cmd, Atribuicao):
            if isinstance(cmd.alvo, Variavel):
                self._obter(cmd.alvo.nome)
            elif isinstance(cmd.alvo, AcessoArray):
                simb = self._obter(cmd.alvo.nome)
                if len(cmd.alvo.indices) != len(simb.dims):
                    raise ErroSemantico("Atribuição em array requer todos os índices")
            self._tipo_expr(cmd.expr)
            return
        if isinstance(cmd, Mostra):
            self._tipo_expr(cmd.expr)
            return
        if isinstance(cmd, Entrada):
            # permitir leitura em escalar, elemento de array ou string em dorzona (char[N])
            if isinstance(cmd.alvo, Variavel):
                simb = self._obter(cmd.alvo.nome)
                return
            elif isinstance(cmd.alvo, AcessoArray):
                simb = self._obter(cmd.alvo.nome)
                if len(cmd.alvo.indices) != len(simb.dims):
                    raise ErroSemantico("Para ler elemento de array, todos os índices devem ser informados")
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

# ------------------
#  Geração de Código C (V2.1)
# ------------------

class GeradorCodigo:
    def __init__(self, prog: Programa, sem: AnalisadorSemantico):
        self.prog = prog
        self.sem = sem
        self.linhas: List[str] = []

    def gerar(self) -> str:
        self.linhas = [
            "#include <stdio.h>",
            "#include <string.h>",
            "#include <locale.h>",
            "",
            "int main(void) {",
        ]

        # declarações no topo (mantido)
        for nome, simb in self.sem.tabela.items():
            self.linhas.append("    " + self._decl_c(nome, simb) + ";")

        # configurar locale para UTF-8 / acentuação no Windows
        self.linhas.append('    setlocale(LC_ALL, "");')

        # comandos
        for cmd in self.prog.comandos:
            self._emit_cmd(cmd, indent=1)

        self.linhas.append("    return 0;")
        self.linhas.append("}")
        return "\n".join(self.linhas)

    # Declaração C (escalares e arrays)
    def _decl_c(self, nome: str, simb: Simbolo) -> str:
        base = simb.tipo_base
        if len(simb.dims) == 0:
            return f"{base} {nome}"
        # arrays
        dims = "".join(f"[{d}]" for d in simb.dims)
        return f"{base} {nome}{dims}"

    def _indent(self, n: int) -> str:
        return "    " * n
    
    def _escape_c_string(self, s: str) -> str:
        # 1) interpretar escapes vindos da DSL (duas chars '\'+'n' -> controle real)
        s = s.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r').replace('\\0', '\0')

        # 2) escapar para literal C
        s = s.replace('\\', '\\\\').replace('"', '\\"')

        # 3) re-materializar controles como escapes visuais em C
        s = s.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r').replace('\0', '\\0')
        return s

    def _emit_cmd(self, cmd: Comando, indent: int) -> None:
        if isinstance(cmd, Comentario):
            self.linhas.append(self._indent(indent) + f"/* {cmd.texto} */")
            return

        if isinstance(cmd, DeclaracaoVar):
            # já declaradas no topo; aqui só inicializamos se houver valor e for escalar
            if cmd.inicial is not None and len(cmd.dims) == 0:
                self.linhas.append(self._indent(indent) + f"{cmd.nome} = {self._emit_expr(cmd.inicial)};")
            return

        if isinstance(cmd, Atribuicao):
            self.linhas.append(self._indent(indent) + f"{self._emit_lvalue(cmd.alvo)} = {self._emit_expr(cmd.expr)};")
            return

        if isinstance(cmd, ExpressaoStmt):
            self.linhas.append(self._indent(indent) + f"{self._emit_expr(cmd.expr)};")
            return

        if isinstance(cmd, Mostra):
            fmt, args = self._montar_printf(cmd.expr)

            # importante: escapar seguro p/ C (normaliza \n, \t, etc. e depois re-escapa)
            fmt_esc = self._escape_c_string(fmt)

            if args:
                self.linhas.append(self._indent(indent) + f'printf(u8"{fmt_esc}", {", ".join(args)});')
            else:
                self.linhas.append(self._indent(indent) + f'printf(u8"{fmt_esc}");')
            return

        if isinstance(cmd, Entrada):
            self._emit_entrada(cmd, indent)
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
            p1 = ""
            if isinstance(cmd.inicial, DeclaracaoVar):
                if cmd.inicial.inicial is not None and len(cmd.inicial.dims) == 0:
                    p1 = f"{cmd.inicial.nome} = {self._emit_expr(cmd.inicial.inicial)}"
            elif isinstance(cmd.inicial, Atribuicao):
                p1 = f"{self._emit_lvalue(cmd.inicial.alvo)} = {self._emit_expr(cmd.inicial.expr)}"
            elif isinstance(cmd.inicial, ExpressaoStmt):
                p1 = f"{self._emit_expr(cmd.inicial.expr)}"

            p2 = self._emit_expr(cmd.cond) if cmd.cond else ""

            if isinstance(cmd.passo, Atribuicao):
                p3 = f"{self._emit_lvalue(cmd.passo.alvo)} = {self._emit_expr(cmd.passo.expr)}"
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

    # Entrada segura
    def _emit_entrada(self, cmd: Entrada, indent: int) -> None:
        # leitura em variável escalar, elemento de array, ou string em char[N] (dorzona)
        if isinstance(cmd.alvo, Variavel):
            simb = self.sem.tabela[cmd.alvo.nome]
            if len(simb.dims) == 0:
                spec = SCANF_FMT.get(simb.tipo_base, "%d")
                self.linhas.append(self._indent(indent) + f'if (scanf("{spec}", &{cmd.alvo.nome}) != 1) {{ fprintf(stderr, "Entrada inválida\\n"); return 1; }}')
            else:
                # leitura de string inteira em char[N] (sem índices): usar largura segura %Ns
                if simb.tipo_base == "char" and len(simb.dims) == 1:
                        largura = max(1, simb.dims[0] - 1)  # deixa 1 byte para '\0'
                        # Dobrar chaves para que f-string não interprete as chaves do bloco C.
                        # Escapar '\n' para que o C receba a sequência '\n' na string.
                        self.linhas.append(self._indent(indent) + f'if (scanf("%{largura}s", {cmd.alvo.nome}) != 1) {{ fprintf(stderr, "Entrada inválida\\n"); return 1; }}')
                else:
                    raise RuntimeError("entradaAi: apenas char[N] sem índices é suportado para leitura de arrays completos")
        elif isinstance(cmd.alvo, AcessoArray):
            # ler elemento específico
            expr_c = f"{cmd.alvo.nome}" + "".join(f"[{self._emit_expr(idx)}]" for idx in cmd.alvo.indices)
            simb = self.sem.tabela[cmd.alvo.nome]
            spec = SCANF_FMT.get(simb.tipo_base, "%d")
            if simb.tipo_base == "char" and len(simb.dims) == len(cmd.alvo.indices):
                # elemento char: precisa de ' %c' e &expr
                spec = SCANF_FMT["char"]
            self.linhas.append(self._indent(indent) + f'if (scanf("{spec}", &({expr_c})) != 1) {{ fprintf(stderr, "Entrada inválida\\n"); return 1; }}')
        else:
            raise RuntimeError("entradaAi: alvo inválido")

    # printf com concatenação e %s para char[]
    def _montar_printf(self, expr: Expr) -> Tuple[str, List[str]]:
        
        def _escape_fmt_literal(s: str) -> str:
            # Escapar apenas aspas e percent em literais do formato.
            return s.replace('"', r'\"').replace('%', '%%')

        partes = self._flatten_concat(expr)
        fmt_parts: List[str] = []
        args: List[str] = []

        for p in partes:
            if isinstance(p, str):
                fmt_parts.append(_escape_fmt_literal(p))
            else:
                tipo = self._inferir_tipo_expr(p)
                if tipo == "string":
                    fmt_parts.append("%s")
                else:
                    spec = PRINTF_FMT.get(tipo, "%g")
                    fmt_parts.append(spec)
                args.append(self._emit_expr(p))

        return "".join(fmt_parts), args

    def _flatten_concat(self, expr: Expr) -> List[Union[str, Expr]]:
        if isinstance(expr, Binario) and expr.op == "+":
            return self._flatten_concat(expr.esq) + self._flatten_concat(expr.dir)
        if isinstance(expr, LiteralString):
            # NÃO decodificar escapes; manter , 	, etc. como texto,
            # para o C interpretar corretamente dentro do printf.
            return [expr.valor]
        return [expr]

    def _inferir_tipo_expr(self, e: Expr) -> str:
        if isinstance(e, LiteralNumero):
            return "double" if e.eh_float else "int"
        if isinstance(e, LiteralString):
            return "string"
        if isinstance(e, Variavel):
            simb = self.sem.tabela.get(e.nome)
            if simb:
                if simb.tipo_base == "char" and len(simb.dims) == 1:
                    return "string"  # char[] -> %s
                return simb.tipo_base
            return "int"
        if isinstance(e, AcessoArray):
            simb = self.sem.tabela.get(e.nome)
            if simb:
                if simb.tipo_base == "char" and len(e.indices) < len(simb.dims):
                    return "string"
                return simb.tipo_base
            return "int"
        if isinstance(e, Binario):
            te = self._inferir_tipo_expr(e.esq)
            td = self._inferir_tipo_expr(e.dir)
            if te == "string" or td == "string":
                return "string"
            ordem = {"int": 0, "float": 1, "double": 2, "char": 0}
            return ["int", "float", "double"][max(ordem.get(te,0), ordem.get(td,0))]
        if isinstance(e, Unario):
            return self._inferir_tipo_expr(e.expr)
        return "int"

    def _emit_lvalue(self, l: LValue) -> str:
        if isinstance(l, Variavel):
            return l.nome
        if isinstance(l, AcessoArray):
            return l.nome + "".join(f"[{self._emit_expr(idx)}]" for idx in l.indices)
        raise RuntimeError("LValue não suportado")
    
    def _emit_expr(self, e: Expr) -> str:
        if isinstance(e, LiteralNumero):
            return str(e.valor)
        if isinstance(e, LiteralString):
            s = self._escape_c_string(e.valor)
            return 'u8"' + s + '"'
        if isinstance(e, Variavel) or isinstance(e, AcessoArray):
            return self._emit_lvalue(e)  # ambos válidos como expr
        if isinstance(e, Unario):
            return f"({e.op}{self._emit_expr(e.expr)})"
        if isinstance(e, Binario):
            if e.op == "=" and isinstance(e.esq, LValue):
                return f"({self._emit_lvalue(e.esq)} = {self._emit_expr(e.dir)})"
            return f"({self._emit_expr(e.esq)} {e.op} {self._emit_expr(e.dir)})"
        raise RuntimeError(f"Expressão não suportada: {e}")

# ------------------
#  Pipeline
# ------------------

def traduzir(codigo_fonte: str) -> str:
    lexico = AnalisadorLexico(codigo_fonte)
    tokens = lexico.tokenizar()

    parser = AnalisadorSintatico(tokens)
    prog = parser.analisar_programa()

    sem = AnalisadorSemantico()
    sem.analisar(prog)

    gerador = GeradorCodigo(prog, sem)
    return gerador.gerar()

# Execução do C gerado (opcional)
def executar_codigo_c(codigo_c: str, nome_arquivo: str = "saida.c"):
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(codigo_c)
    subprocess.run(["gcc", nome_arquivo, "-o", "saida_exec"], check=True)
    resultado = subprocess.run(["./saida_exec"], capture_output=True, text=True)
    print("\n=== Saída do programa em C ===")
    print(resultado.stdout)

# CLI
def main():
    parser_arg = argparse.ArgumentParser(description="Compilador (Tokens->Parser->AST->CodeGen) VoidKnee -> C (V2.1)")
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
