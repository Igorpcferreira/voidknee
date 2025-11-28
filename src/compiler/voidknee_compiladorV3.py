
"""
VoidKnee 🦵 → C / Assembly (V3)

Versão didática do compilador da linguagem VoidKnee com:
- Casting explícito (estilo C): (inteirao) expr, (flutuante) expr, ...
- Funções e recursão: inteirao f(inteirao n) { ... retorna ...; }
- Erros didáticos com linha/coluna e mensagem amigável.
- Níveis de "otimização" O0/O1/O2 (dobrando o pipeline com algumas otimizações simples).
- Backend alternativo para "assembly" de uma máquina de pilha fictícia.

Interface principal:
    traduzir(fonte: str, backend: str = "c", otimizacao: str = "O0") -> str

O backend "c" gera um programa C completo.
O backend "asm" gera assembly de uma máquina de pilha didática (não é x86 real).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Dict, Tuple, Any


# =========================================
#  Erros didáticos
# =========================================

class ErroCompilacaoVoidKnee(Exception):
    def __init__(self, mensagem: str, linha: int, coluna: int, etapa: str):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.linha = linha
        self.coluna = coluna
        self.etapa = etapa  # "léxico", "sintático", "semântico"

    def __str__(self) -> str:
        return f"[{self.etapa} erro] linha {self.linha}, coluna {self.coluna}: {self.mensagem}"


# =========================================
#  Léxico
# =========================================

class TokenTipo(Enum):
    IDENT = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    CHAR = auto()

    # Palavras-chave
    TIPO = auto()
    KW_SE = auto()
    KW_SENAO = auto()
    KW_ENQUANTO = auto()
    KW_PARA = auto()
    KW_RETORNA = auto()
    KW_TRUE = auto()
    KW_FALSE = auto()

    # Funções built-in
    KW_MOSTRA = auto()
    KW_ENTRADA = auto()

    # Símbolos
    OP = auto()
    PONT = auto()
    EOF = auto()


TIPOS_PALAVRAS = {
    "inteirao",
    "flutuante",
    "dobradura",
    "dorzinha",
    "dorzona",
    "verdadeQueDoi",
}

PALAVRAS_CHAVE = {
    "sejoelho": TokenTipo.KW_SE,
    "outracoisa": TokenTipo.KW_SENAO,
    "enquantoDoi": TokenTipo.KW_ENQUANTO,
    "praCada": TokenTipo.KW_PARA,
    "retorna": TokenTipo.KW_RETORNA,
    "verdadeiro": TokenTipo.KW_TRUE,
    "falso": TokenTipo.KW_FALSE,
    "mostraAi": TokenTipo.KW_MOSTRA,
    "entradaAi": TokenTipo.KW_ENTRADA,
}


@dataclass
class Token:
    tipo: TokenTipo
    lexema: str
    linha: int
    coluna: int


class Lexer:
    def __init__(self, fonte: str):
        self.fonte = fonte
        self.i = 0
        self.linha = 1
        self.coluna = 1

    def _atual(self) -> str:
        if self.i >= len(self.fonte):
            return "\0"
        return self.fonte[self.i]

    def _avancar(self) -> str:
        ch = self._atual()
        self.i += 1
        if ch == "\n":
            self.linha += 1
            self.coluna = 1
        else:
            self.coluna += 1
        return ch

    def _match(self, esperado: str) -> bool:
        if self._atual() == esperado:
            self._avancar()
            return True
        return False

    def _pular_espacos_e_comentarios(self):
        while True:
            ch = self._atual()
            if ch in " \t\r\n":
                self._avancar()
            elif ch == "/" and self._peek() == "/":
                # comentário de linha
                while self._atual() not in ("\n", "\0"):
                    self._avancar()
            elif ch == "/" and self._peek() == "*":
                # comentário de bloco
                self._avancar()  # /
                self._avancar()  # *
                while not (self._atual() == "*" and self._peek() == "/"):
                    if self._atual() == "\0":
                        raise ErroCompilacaoVoidKnee(
                            "Comentário de bloco não fechado (/* ... */).",
                            self.linha,
                            self.coluna,
                            "léxico",
                        )
                    self._avancar()
                self._avancar()  # *
                self._avancar()  # /
            elif ch == "/" and self._peek() == "/":
                while self._atual() not in ("\n", "\0"):
                    self._avancar()
            else:
                break

    def _peek(self) -> str:
        if self.i + 1 >= len(self.fonte):
            return "\0"
        return self.fonte[self.i + 1]

    def tokens(self) -> List[Token]:
        toks: List[Token] = []
        while True:
            self._pular_espacos_e_comentarios()
            inicio_linha = self.linha
            inicio_coluna = self.coluna
            ch = self._atual()
            if ch == "\0":
                toks.append(Token(TokenTipo.EOF, "", inicio_linha, inicio_coluna))
                break

            # Identificadores / palavras-chave / tipos
            if ch.isalpha() or ch == "_":
                lex = []
                while self._atual().isalnum() or self._atual() == "_":
                    lex.append(self._avancar())
                lexema = "".join(lex)
                if lexema in TIPOS_PALAVRAS:
                    toks.append(Token(TokenTipo.TIPO, lexema, inicio_linha, inicio_coluna))
                elif lexema in PALAVRAS_CHAVE:
                    toks.append(Token(PALAVRAS_CHAVE[lexema], lexema, inicio_linha, inicio_coluna))
                else:
                    toks.append(Token(TokenTipo.IDENT, lexema, inicio_linha, inicio_coluna))
                continue

            # Números
            if ch.isdigit():
                lex = []
                tem_ponto = False
                while self._atual().isdigit() or (self._atual() == "." and not tem_ponto):
                    if self._atual() == ".":
                        tem_ponto = True
                    lex.append(self._avancar())
                lexema = "".join(lex)
                if tem_ponto:
                    toks.append(Token(TokenTipo.FLOAT, lexema, inicio_linha, inicio_coluna))
                else:
                    toks.append(Token(TokenTipo.INT, lexema, inicio_linha, inicio_coluna))
                continue

            # String
            if ch == '"':
                self._avancar()
                lex = []
                while self._atual() not in ('"', "\0"):
                    c = self._avancar()
                    if c == "\\":
                        # escape simples
                        c2 = self._avancar()
                        if c2 == "n":
                            lex.append("\\n")
                        elif c2 == "t":
                            lex.append("\\t")
                        else:
                            lex.append("\\" + c2)
                    else:
                        lex.append(c)
                if self._atual() != '"':
                    raise ErroCompilacaoVoidKnee(
                        "String não fechada. Lembre de colocar o \" final.",
                        inicio_linha,
                        inicio_coluna,
                        "léxico",
                    )
                self._avancar()
                toks.append(Token(TokenTipo.STRING, "".join(lex), inicio_linha, inicio_coluna))
                continue

            # Char
            if ch == "'":
                self._avancar()
                c = self._avancar()
                if c == "\\":
                    # escape
                    c2 = self._avancar()
                    if c2 == "n":
                        val = "\\n"
                    elif c2 == "t":
                        val = "\\t"
                    else:
                        val = "\\" + c2
                else:
                    val = c
                if self._atual() != "'":
                    raise ErroCompilacaoVoidKnee(
                        "Caractere não fechado. Use algo como 'a'.",
                        inicio_linha,
                        inicio_coluna,
                        "léxico",
                    )
                self._avancar()
                toks.append(Token(TokenTipo.CHAR, val, inicio_linha, inicio_coluna))
                continue

            # Operadores de múltiplos chars
            two = ch + self._peek()
            if two in ("==", "!=", "<=", ">=", "&&", "||", "++", "--"):
                self._avancar()
                self._avancar()
                toks.append(Token(TokenTipo.OP, two, inicio_linha, inicio_coluna))
                continue

            # Operadores simples
            if ch in "+-*/%=!<>":
                self._avancar()
                toks.append(Token(TokenTipo.OP, ch, inicio_linha, inicio_coluna))
                continue

            # Pontuação
            if ch in "();{},[]":
                self._avancar()
                toks.append(Token(TokenTipo.PONT, ch, inicio_linha, inicio_coluna))
                continue

            # Caractere desconhecido
            raise ErroCompilacaoVoidKnee(
                f"Caractere inesperado: '{ch}'.",
                inicio_linha,
                inicio_coluna,
                "léxico",
            )

        return toks


# =========================================
#  AST
# =========================================

class TipoPrimitivo(Enum):
    INTEIRO = auto()
    FLUTUANTE = auto()
    DOBRADURA = auto()
    CHAR = auto()
    STRING = auto()
    BOOL = auto()
    VOID = auto()


@dataclass
class Tipo:
    prim: TipoPrimitivo

    def __str__(self) -> str:
        return self.prim.name


TIPO_POR_NOME: Dict[str, Tipo] = {
    "inteirao": Tipo(TipoPrimitivo.INTEIRO),
    "flutuante": Tipo(TipoPrimitivo.FLUTUANTE),
    "dobradura": Tipo(TipoPrimitivo.DOBRADURA),
    "dorzinha": Tipo(TipoPrimitivo.CHAR),
    "dorzona": Tipo(TipoPrimitivo.STRING),
    "verdadeQueDoi": Tipo(TipoPrimitivo.BOOL),
}


def tipo_c(t: Tipo) -> str:
    if t.prim == TipoPrimitivo.INTEIRO:
        return "int"
    if t.prim == TipoPrimitivo.FLUTUANTE:
        return "float"
    if t.prim == TipoPrimitivo.DOBRADURA:
        return "double"
    if t.prim == TipoPrimitivo.CHAR:
        return "char"
    if t.prim == TipoPrimitivo.STRING:
        return "char*"
    if t.prim == TipoPrimitivo.BOOL:
        return "int"  # bool didático como int 0/1
    if t.prim == TipoPrimitivo.VOID:
        return "void"
    raise ValueError("Tipo desconhecido")


# --- Nós de AST ---

@dataclass
class Expr:
    linha: int
    coluna: int


@dataclass
class Literal(Expr):
    valor: Any
    tipo: Tipo


@dataclass
class VarRef(Expr):
    nome: str


@dataclass
class BinOp(Expr):
    op: str
    esquerda: Expr
    direita: Expr


@dataclass
class UnOp(Expr):
    op: str
    expr: Expr


@dataclass
class Assign(Expr):
    nome: str
    expr: Expr


@dataclass
class Call(Expr):
    nome: str
    argumentos: List[Expr]


@dataclass
class Cast(Expr):
    tipo_destino: Tipo
    expr: Expr


# --- Statements ---

@dataclass
class Stmt:
    linha: int
    coluna: int


@dataclass
class VarDecl(Stmt):
    tipo: Tipo
    nome: str
    init: Optional[Expr]


@dataclass
class ExprStmt(Stmt):
    expr: Expr


@dataclass
class ReturnStmt(Stmt):
    expr: Optional[Expr]


@dataclass
class IfStmt(Stmt):
    cond: Expr
    entao: "Block"
    senao: Optional["Block"]


@dataclass
class WhileStmt(Stmt):
    cond: Expr
    corpo: "Block"


@dataclass
class ForStmt(Stmt):
    init: Optional[Stmt]
    cond: Optional[Expr]
    passo: Optional[Expr]
    corpo: "Block"


@dataclass
class Block(Stmt):
    stmts: List[Stmt]


@dataclass
class Param:
    tipo: Tipo
    nome: str


@dataclass
class FuncDecl:
    tipo_retorno: Tipo
    nome: str
    params: List[Param]
    corpo: Block
    linha: int
    coluna: int


@dataclass
class Programa:
    funcoes: List[FuncDecl]
    globais: List[VarDecl]


# =========================================
#  Parser (descida recursiva)
# =========================================

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.i = 0

    def _atual(self) -> Token:
        return self.tokens[self.i]

    def _consumir(self, tipo: Optional[TokenTipo] = None, lexema: Optional[str] = None, msg: str = "") -> Token:
        tok = self._atual()
        if tipo is not None and tok.tipo != tipo:
            raise ErroCompilacaoVoidKnee(
                msg or f"Esperado token {tipo.name}, mas encontrado {tok.lexema}.",
                tok.linha,
                tok.coluna,
                "sintático",
            )
        if lexema is not None and tok.lexema != lexema:
            raise ErroCompilacaoVoidKnee(
                msg or f"Esperado '{lexema}', mas encontrado '{tok.lexema}'.",
                tok.linha,
                tok.coluna,
                "sintático",
            )
        self.i += 1
        return tok

    def _match(self, *tipos_lexemas) -> Optional[Token]:
        tok = self._atual()
        for tipo, lex in tipos_lexemas:
            if tok.tipo == tipo and (lex is None or tok.lexema == lex):
                self.i += 1
                return tok
        return None

    def parse(self) -> Programa:
        globais: List[VarDecl] = []
        funcoes: List[FuncDecl] = []

        while self._atual().tipo != TokenTipo.EOF:
            # tipo
            if self._atual().tipo != TokenTipo.TIPO:
                tok = self._atual()
                raise ErroCompilacaoVoidKnee(
                    f"Esperado tipo (ex.: inteirao, flutuante) no início de declaração ou função, encontrado '{tok.lexema}'.",
                    tok.linha,
                    tok.coluna,
                    "sintático",
                )
            tipo_tok = self._consumir(TokenTipo.TIPO)
            tipo = TIPO_POR_NOME[tipo_tok.lexema]

            ident = self._consumir(TokenTipo.IDENT, msg="Esperado nome de variável ou função.")

            if self._match((TokenTipo.PONT, "(")):
                # função
                params = self._parametros_funcao()
                corpo = self._bloco()
                funcoes.append(FuncDecl(tipo, ident.lexema, params, corpo, tipo_tok.linha, tipo_tok.coluna))
            else:
                # variável global
                init_expr = None
                if self._match((TokenTipo.OP, "=")):
                    init_expr = self._expressao()
                self._consumir(TokenTipo.PONT, ";", "Faltando ';' após declaração de variável.")
                globais.append(VarDecl(tipo=tipo, nome=ident.lexema, init=init_expr, linha=ident.linha, coluna=ident.coluna))

        return Programa(funcoes, globais)

    def _parametros_funcao(self) -> List[Param]:
        params: List[Param] = []
        if self._match((TokenTipo.PONT, ")")):
            return params
        while True:
            tipo_tok = self._consumir(TokenTipo.TIPO, msg="Esperado tipo do parâmetro da função.")
            nome_tok = self._consumir(TokenTipo.IDENT, msg="Esperado nome do parâmetro da função.")
            params.append(Param(TIPO_POR_NOME[tipo_tok.lexema], nome_tok.lexema))
            if self._match((TokenTipo.PONT, ")")):
                break
            self._consumir(TokenTipo.PONT, ",", "Esperado ',' ou ')' na lista de parâmetros.")
        return params

    def _bloco(self) -> Block:
        brace = self._consumir(TokenTipo.PONT, "{", "Esperado '{' para iniciar bloco.")
        stmts: List[Stmt] = []
        while not (self._atual().tipo == TokenTipo.PONT and self._atual().lexema == "}"):
            stmts.append(self._declaracao_ou_stmt())
        self._consumir(TokenTipo.PONT, "}", "Esperado '}' para fechar bloco.")
        return Block(stmts=stmts, linha=brace.linha, coluna=brace.coluna)

    def _declaracao_ou_stmt(self) -> Stmt:
        # declaração local
        if self._atual().tipo == TokenTipo.TIPO:
            tipo_tok = self._consumir(TokenTipo.TIPO)
            tipo = TIPO_POR_NOME[tipo_tok.lexema]
            nome_tok = self._consumir(TokenTipo.IDENT, msg="Esperado nome da variável.")
            init_expr = None
            if self._match((TokenTipo.OP, "=")):
                init_expr = self._expressao()
            self._consumir(TokenTipo.PONT, ";", "Faltando ';' após declaração de variável.")
            return VarDecl(tipo=tipo, nome=nome_tok.lexema, init=init_expr, linha=nome_tok.linha, coluna=nome_tok.coluna)
        return self._stmt()

    def _stmt(self) -> Stmt:
        tok = self._atual()
        # if
        if tok.tipo == TokenTipo.KW_SE:
            return self._if_stmt()
        # while
        if tok.tipo == TokenTipo.KW_ENQUANTO:
            return self._while_stmt()
        # for
        if tok.tipo == TokenTipo.KW_PARA:
            return self._for_stmt()
        # return
        if tok.tipo == TokenTipo.KW_RETORNA:
            self._consumir(TokenTipo.KW_RETORNA)
            if self._atual().tipo == TokenTipo.PONT and self._atual().lexema == ";":
                sem = self._consumir(TokenTipo.PONT, ";")
                return ReturnStmt(expr=None, linha=tok.linha, coluna=tok.coluna)
            expr = self._expressao()
            self._consumir(TokenTipo.PONT, ";", "Faltando ';' após retorna.")
            return ReturnStmt(expr=expr, linha=tok.linha, coluna=tok.coluna)
        # bloco
        if tok.tipo == TokenTipo.PONT and tok.lexema == "{":
            return self._bloco()
        # expressão
        expr = self._expressao()
        self._consumir(TokenTipo.PONT, ";", "Faltando ';' após expressão.")
        return ExprStmt(expr=expr, linha=tok.linha, coluna=tok.coluna)

    def _if_stmt(self) -> IfStmt:
        tok_if = self._consumir(TokenTipo.KW_SE)
        self._consumir(TokenTipo.PONT, "(", "Esperado '(' após 'sejoelho'.")
        cond = self._expressao()
        self._consumir(TokenTipo.PONT, ")", "Esperado ')' após condição do 'sejoelho'.")
        entao = self._bloco()
        senao = None
        if self._match((TokenTipo.KW_SENAO, None)):
            senao = self._bloco()
        return IfStmt(cond=cond, entao=entao, senao=senao, linha=tok_if.linha, coluna=tok_if.coluna)

    def _while_stmt(self) -> WhileStmt:
        tok_w = self._consumir(TokenTipo.KW_ENQUANTO)
        self._consumir(TokenTipo.PONT, "(", "Esperado '(' após 'enquantoDoi'.")
        cond = self._expressao()
        self._consumir(TokenTipo.PONT, ")", "Esperado ')' após condição do 'enquantoDoi'.")
        corpo = self._bloco()
        return WhileStmt(cond=cond, corpo=corpo, linha=tok_w.linha, coluna=tok_w.coluna)

    def _for_stmt(self) -> ForStmt:
        tok_for = self._consumir(TokenTipo.KW_PARA)
        self._consumir(TokenTipo.PONT, "(", "Esperado '(' após 'praCada'.")
        init: Optional[Stmt] = None
        if not (self._atual().tipo == TokenTipo.PONT and self._atual().lexema == ";"):
            # pode ser declaração ou expressão
            if self._atual().tipo == TokenTipo.TIPO:
                init = self._declaracao_ou_stmt()
            else:
                expr = self._expressao()
                self._consumir(TokenTipo.PONT, ";", "Faltando ';' na parte inicial do 'praCada'.")
                init = ExprStmt(expr=expr, linha=expr.linha, coluna=expr.coluna)
        else:
            self._consumir(TokenTipo.PONT, ";")

        cond: Optional[Expr] = None
        if not (self._atual().tipo == TokenTipo.PONT and self._atual().lexema == ";"):
            cond = self._expressao()
        self._consumir(TokenTipo.PONT, ";", "Faltando ';' na condição do 'praCada'.")

        passo: Optional[Expr] = None
        if not (self._atual().tipo == TokenTipo.PONT and self._atual().lexema == ")"):
            passo = self._expressao()
        self._consumir(TokenTipo.PONT, ")", "Esperado ')' após cabeçalho do 'praCada'.")

        corpo = self._bloco()
        return ForStmt(init=init, cond=cond, passo=passo, corpo=corpo, linha=tok_for.linha, coluna=tok_for.coluna)

    # --- expressões ---

    def _expressao(self) -> Expr:
        return self._atribuicao()

    def _atribuicao(self) -> Expr:
        expr = self._ou_logico()
        if self._atual().tipo == TokenTipo.OP and self._atual().lexema == "=":
            op_tok = self._consumir(TokenTipo.OP, "=")
            if not isinstance(expr, VarRef):
                raise ErroCompilacaoVoidKnee(
                    "O lado esquerdo de uma atribuição precisa ser um nome de variável.",
                    expr.linha,
                    expr.coluna,
                    "sintático",
                )
            valor = self._atribuicao()
            return Assign(nome=expr.nome, expr=valor, linha=op_tok.linha, coluna=op_tok.coluna)
        return expr

    def _ou_logico(self) -> Expr:
        expr = self._e_logico()
        while self._atual().tipo == TokenTipo.OP and self._atual().lexema == "||":
            tok = self._consumir(TokenTipo.OP, "||")
            direito = self._e_logico()
            expr = BinOp(op="||", esquerda=expr, direita=direito, linha=tok.linha, coluna=tok.coluna)
        return expr

    def _e_logico(self) -> Expr:
        expr = self._igualdade()
        while self._atual().tipo == TokenTipo.OP and self._atual().lexema == "&&":
            tok = self._consumir(TokenTipo.OP, "&&")
            direito = self._igualdade()
            expr = BinOp(op="&&", esquerda=expr, direita=direito, linha=tok.linha, coluna=tok.coluna)
        return expr

    def _igualdade(self) -> Expr:
        expr = self._comparacao()
        while self._atual().tipo == TokenTipo.OP and self._atual().lexema in ("==", "!="):
            tok = self._atual()
            self._avancar()
            direito = self._comparacao()
            expr = BinOp(op=tok.lexema, esquerda=expr, direita=direito, linha=tok.linha, coluna=tok.coluna)
        return expr

    def _comparacao(self) -> Expr:
        expr = self._termo()
        while self._atual().tipo == TokenTipo.OP and self._atual().lexema in ("<", ">", "<=", ">="):
            tok = self._atual()
            self._avancar()
            direito = self._termo()
            expr = BinOp(op=tok.lexema, esquerda=expr, direita=direito, linha=tok.linha, coluna=tok.coluna)
        return expr

    def _termo(self) -> Expr:
        expr = self._fator()
        while self._atual().tipo == TokenTipo.OP and self._atual().lexema in ("+", "-"):
            tok = self._atual()
            self._avancar()
            direito = self._fator()
            expr = BinOp(op=tok.lexema, esquerda=expr, direita=direito, linha=tok.linha, coluna=tok.coluna)
        return expr

    def _fator(self) -> Expr:
        expr = self._unario()
        while self._atual().tipo == TokenTipo.OP and self._atual().lexema in ("*", "/"):
            tok = self._atual()
            self._avancar()
            direito = self._unario()
            expr = BinOp(op=tok.lexema, esquerda=expr, direita=direito, linha=tok.linha, coluna=tok.coluna)
        return expr

    def _unario(self) -> Expr:
        tok = self._atual()
        if tok.tipo == TokenTipo.OP and tok.lexema in ("!", "-"):
            self._avancar()
            expr = self._unario()
            return UnOp(op=tok.lexema, expr=expr, linha=tok.linha, coluna=tok.coluna)
        return self._cast()

    def _cast(self) -> Expr:
        """
        Casting estilo C: (inteirao) expr, (flutuante) expr, etc.
        Se não encaixar como cast, cai como agrupamento normal.
        """
        if self._atual().tipo == TokenTipo.PONT and self._atual().lexema == "(":
            # lookahead para ver se é (TIPO)
            salva_i = self.i
            salva_tok = self._atual()
            self._consumir(TokenTipo.PONT, "(")
            if self._atual().tipo == TokenTipo.TIPO:
                tipo_tok = self._consumir(TokenTipo.TIPO)
                if self._atual().tipo == TokenTipo.PONT and self._atual().lexema == ")":
                    self._consumir(TokenTipo.PONT, ")")
                    expr = self._cast()
                    return Cast(tipo_destino=TIPO_POR_NOME[tipo_tok.lexema], expr=expr, linha=tipo_tok.linha, coluna=tipo_tok.coluna)
            # não era cast; volta
            self.i = salva_i
        return self._primario()

    def _primario(self) -> Expr:
        tok = self._atual()
        if tok.tipo == TokenTipo.INT:
            self._avancar()
            return Literal(valor=int(tok.lexema), tipo=Tipo(TipoPrimitivo.INTEIRO), linha=tok.linha, coluna=tok.coluna)
        if tok.tipo == TokenTipo.FLOAT:
            self._avancar()
            return Literal(valor=float(tok.lexema), tipo=Tipo(TipoPrimitivo.FLUTUANTE), linha=tok.linha, coluna=tok.coluna)
        if tok.tipo == TokenTipo.STRING:
            self._avancar()
            return Literal(valor=tok.lexema, tipo=Tipo(TipoPrimitivo.STRING), linha=tok.linha, coluna=tok.coluna)
        if tok.tipo == TokenTipo.CHAR:
            self._avancar()
            return Literal(valor=tok.lexema, tipo=Tipo(TipoPrimitivo.CHAR), linha=tok.linha, coluna=tok.coluna)
        if tok.tipo == TokenTipo.KW_TRUE:
            self._avancar()
            return Literal(valor=1, tipo=Tipo(TipoPrimitivo.BOOL), linha=tok.linha, coluna=tok.coluna)
        if tok.tipo == TokenTipo.KW_FALSE:
            self._avancar()
            return Literal(valor=0, tipo=Tipo(TipoPrimitivo.BOOL), linha=tok.linha, coluna=tok.coluna)
        if tok.tipo == TokenTipo.IDENT or tok.tipo in (TokenTipo.KW_MOSTRA, TokenTipo.KW_ENTRADA):
            self._avancar()
            nome = tok.lexema
            if self._atual().tipo == TokenTipo.PONT and self._atual().lexema == "(":
                self._consumir(TokenTipo.PONT, "(")
                args: List[Expr] = []
                if not (self._atual().tipo == TokenTipo.PONT and self._atual().lexema == ")"):
                    while True:
                        args.append(self._expressao())
                        if self._atual().tipo == TokenTipo.PONT and self._atual().lexema == ")":
                            break
                        self._consumir(TokenTipo.PONT, ",", "Esperado ',' ou ')' na lista de argumentos.")
                self._consumir(TokenTipo.PONT, ")")
                return Call(nome=nome, argumentos=args, linha=tok.linha, coluna=tok.coluna)
            return VarRef(nome=nome, linha=tok.linha, coluna=tok.coluna)
        if tok.tipo == TokenTipo.PONT and tok.lexema == "(":
            self._consumir(TokenTipo.PONT, "(")
            expr = self._expressao()
            self._consumir(TokenTipo.PONT, ")", "Esperado ')' após expressão.")
            return expr

        raise ErroCompilacaoVoidKnee(
            f"Expressão inesperada iniciando com '{tok.lexema}'.",
            tok.linha,
            tok.coluna,
            "sintático",
        )

    def _avancar(self):
        self.i += 1


# =========================================
#  Semântica
# =========================================

class Escopo:
    def __init__(self, pai: Optional["Escopo"] = None):
        self.pai = pai
        self.vars: Dict[str, Tipo] = {}

    def declarar(self, nome: str, tipo: Tipo, linha: int, coluna: int):
        if nome in self.vars:
            raise ErroCompilacaoVoidKnee(
                f"Variável '{nome}' já foi declarada neste escopo.",
                linha,
                coluna,
                "semântico",
            )
        self.vars[nome] = tipo

    def resolver(self, nome: str) -> Optional[Tipo]:
        if nome in self.vars:
            return self.vars[nome]
        if self.pai:
            return self.pai.resolver(nome)
        return None


@dataclass
class AssinaturaFunc:
    retorno: Tipo
    params: List[Param]
    decl: FuncDecl


class AnalisadorSemantico:
    def __init__(self, prog: Programa):
        self.prog = prog
        self.funcoes: Dict[str, AssinaturaFunc] = {}

    def analisar(self):
        # 1) registrar funções
        for f in self.prog.funcoes:
            if f.nome in self.funcoes:
                raise ErroCompilacaoVoidKnee(
                    f"Função '{f.nome}' já foi declarada.",
                    f.linha,
                    f.coluna,
                    "semântico",
                )
            self.funcoes[f.nome] = AssinaturaFunc(f.tipo_retorno, f.params, f)

        # 2) escopo global
        escopo_global = Escopo()
        for g in self.prog.globais:
            escopo_global.declarar(g.nome, g.tipo, g.linha, g.coluna)
            if g.init is not None:
                self._tipo_expr(g.init, escopo_global)

        # 3) funções
        for f in self.prog.funcoes:
            esc_fun = Escopo(escopo_global)
            for p in f.params:
                esc_fun.declarar(p.nome, p.tipo, f.linha, f.coluna)
            self._tipo_bloco(f.corpo, esc_fun, f.tipo_retorno)

        # 4) garantir que exista uma função principal()
        if "principal" not in self.funcoes:
            raise ErroCompilacaoVoidKnee(
                "Programa precisa de uma função 'inteirao principal()' como ponto de entrada.",
                1,
                1,
                "semântico",
            )

    # --- helpers ---

    def _tipo_bloco(self, bloco: Block, escopo: Escopo, tipo_retorno: Tipo):
        for stmt in bloco.stmts:
            self._tipo_stmt(stmt, escopo, tipo_retorno)

    def _tipo_stmt(self, stmt: Stmt, escopo: Escopo, tipo_retorno: Tipo):
        if isinstance(stmt, VarDecl):
            escopo.declarar(stmt.nome, stmt.tipo, stmt.linha, stmt.coluna)
            if stmt.init is not None:
                t = self._tipo_expr(stmt.init, escopo)
                self._verifica_atribuicao(stmt.tipo, t, stmt.linha, stmt.coluna)
            return
        if isinstance(stmt, ExprStmt):
            self._tipo_expr(stmt.expr, escopo)
            return
        if isinstance(stmt, ReturnStmt):
            if stmt.expr is None:
                if tipo_retorno.prim != TipoPrimitivo.VOID:
                    raise ErroCompilacaoVoidKnee(
                        f"Função precisa retornar um valor do tipo {tipo_retorno.prim.name}, mas 'retorna;' sem valor foi usado.",
                        stmt.linha,
                        stmt.coluna,
                        "semântico",
                    )
            else:
                rt = self._tipo_expr(stmt.expr, escopo)
                self._verifica_atribuicao(tipo_retorno, rt, stmt.linha, stmt.coluna)
            return
        if isinstance(stmt, IfStmt):
            ct = self._tipo_expr(stmt.cond, escopo)
            if ct.prim not in (TipoPrimitivo.BOOL, TipoPrimitivo.INTEIRO):
                raise ErroCompilacaoVoidKnee(
                    "Condição do 'sejoelho' deve ser booleana (verdadeiro/falso) ou inteira (0/1).",
                    stmt.cond.linha,
                    stmt.cond.coluna,
                    "semântico",
                )
            esc_then = Escopo(escopo)
            self._tipo_bloco(stmt.entao, esc_then, tipo_retorno)
            if stmt.senao:
                esc_else = Escopo(escopo)
                self._tipo_bloco(stmt.senao, esc_else, tipo_retorno)
            return
        if isinstance(stmt, WhileStmt):
            ct = self._tipo_expr(stmt.cond, escopo)
            if ct.prim not in (TipoPrimitivo.BOOL, TipoPrimitivo.INTEIRO):
                raise ErroCompilacaoVoidKnee(
                    "Condição do 'enquantoDoi' deve ser booleana (verdadeiro/falso) ou inteira (0/1).",
                    stmt.cond.linha,
                    stmt.cond.coluna,
                    "semântico",
                )
            esc_body = Escopo(escopo)
            self._tipo_bloco(stmt.corpo, esc_body, tipo_retorno)
            return
        if isinstance(stmt, ForStmt):
            esc_for = Escopo(escopo)
            if stmt.init:
                self._tipo_stmt(stmt.init, esc_for, tipo_retorno)
            if stmt.cond:
                ct = self._tipo_expr(stmt.cond, esc_for)
                if ct.prim not in (TipoPrimitivo.BOOL, TipoPrimitivo.INTEIRO):
                    raise ErroCompilacaoVoidKnee(
                        "Condição do 'praCada' deve ser booleana (verdadeiro/falso) ou inteira (0/1).",
                        stmt.cond.linha,
                        stmt.cond.coluna,
                        "semântico",
                    )
            if stmt.passo:
                self._tipo_expr(stmt.passo, esc_for)
            self._tipo_bloco(stmt.corpo, esc_for, tipo_retorno)
            return
        if isinstance(stmt, Block):
            esc_bloco = Escopo(escopo)
            self._tipo_bloco(stmt, esc_bloco, tipo_retorno)
            return
        raise RuntimeError(f"Stmt desconhecido: {stmt!r}")

    def _ranking_tipo(self, t: Tipo) -> int:
        # ordem de promoção: bool < int < float < double
        if t.prim == TipoPrimitivo.BOOL:
            return 0
        if t.prim == TipoPrimitivo.INTEIRO:
            return 1
        if t.prim == TipoPrimitivo.FLUTUANTE:
            return 2
        if t.prim == TipoPrimitivo.DOBRADURA:
            return 3
        return -1  # char/string não entram aqui

    def _tipo_promovido(self, a: Tipo, b: Tipo) -> Tipo:
        ra = self._ranking_tipo(a)
        rb = self._ranking_tipo(b)
        if ra == -1 or rb == -1:
            # combinação não numérica, devolve int só para evitar crash; será tratada antes
            return Tipo(TipoPrimitivo.INTEIRO)
        return a if ra >= rb else b

    def _verifica_atribuicao(self, destino: Tipo, fonte: Tipo, linha: int, coluna: int):
        # Permitimos conversões numéricas simples; string/char/bool restringidos.
        if destino.prim == fonte.prim:
            return
        if destino.prim in (TipoPrimitivo.INTEIRO, TipoPrimitivo.FLUTUANTE, TipoPrimitivo.DOBRADURA) and \
           fonte.prim in (TipoPrimitivo.INTEIRO, TipoPrimitivo.FLUTUANTE, TipoPrimitivo.DOBRADURA, TipoPrimitivo.BOOL):
            return
        if destino.prim == TipoPrimitivo.BOOL and fonte.prim in (TipoPrimitivo.INTEIRO, TipoPrimitivo.BOOL):
            return
        raise ErroCompilacaoVoidKnee(
            f"Não é possível atribuir valor do tipo {fonte.prim.name} em variável do tipo {destino.prim.name}. "
            f"Dica: use um casting explícito, ex.: (inteirao) ...",
            linha,
            coluna,
            "semântico",
        )

    def _tipo_expr(self, expr: Expr, escopo: Escopo) -> Tipo:
        if isinstance(expr, Literal):
            return expr.tipo
        if isinstance(expr, VarRef):
            t = escopo.resolver(expr.nome)
            if t is None:
                raise ErroCompilacaoVoidKnee(
                    f"Variável '{expr.nome}' usada antes de ser declarada.",
                    expr.linha,
                    expr.coluna,
                    "semântico",
                )
            return t
        if isinstance(expr, Assign):
            tvar = escopo.resolver(expr.nome)
            if tvar is None:
                raise ErroCompilacaoVoidKnee(
                    f"Variável '{expr.nome}' não foi declarada antes da atribuição.",
                    expr.linha,
                    expr.coluna,
                    "semântico",
                )
            texpr = self._tipo_expr(expr.expr, escopo)
            self._verifica_atribuicao(tvar, texpr, expr.linha, expr.coluna)
            return tvar
        if isinstance(expr, UnOp):
            t = self._tipo_expr(expr.expr, escopo)
            if expr.op == "!":
                if t.prim not in (TipoPrimitivo.BOOL, TipoPrimitivo.INTEIRO):
                    raise ErroCompilacaoVoidKnee(
                        "Operador '!' só pode ser usado com booleano ou inteiro.",
                        expr.linha,
                        expr.coluna,
                        "semântico",
                    )
                return Tipo(TipoPrimitivo.BOOL)
            if expr.op == "-":
                if t.prim not in (TipoPrimitivo.INTEIRO, TipoPrimitivo.FLUTUANTE, TipoPrimitivo.DOBRADURA):
                    raise ErroCompilacaoVoidKnee(
                        "Operador '-' unário só pode ser usado com tipos numéricos.",
                        expr.linha,
                        expr.coluna,
                        "semântico",
                    )
                return t
            return t
        if isinstance(expr, BinOp):
            ta = self._tipo_expr(expr.esquerda, escopo)
            tb = self._tipo_expr(expr.direita, escopo)
            if expr.op in ("+", "-", "*", "/"):
                if ta.prim not in (TipoPrimitivo.INTEIRO, TipoPrimitivo.FLUTUANTE, TipoPrimitivo.DOBRADURA) or \
                   tb.prim not in (TipoPrimitivo.INTEIRO, TipoPrimitivo.FLUTUANTE, TipoPrimitivo.DOBRADURA):
                    raise ErroCompilacaoVoidKnee(
                        f"Operador '{expr.op}' só pode ser usado entre números (inteirao, flutuante, dobradura).",
                        expr.linha,
                        expr.coluna,
                        "semântico",
                    )
                return self._tipo_promovido(ta, tb)
            if expr.op in ("<", ">", "<=", ">=", "==", "!="):
                # comparações numéricas e booleanas
                if ta.prim in (TipoPrimitivo.STRING, TipoPrimitivo.VOID) or \
                   tb.prim in (TipoPrimitivo.STRING, TipoPrimitivo.VOID):
                    raise ErroCompilacaoVoidKnee(
                        "Comparações só são suportadas para números, booleanos e chars.",
                        expr.linha,
                        expr.coluna,
                        "semântico",
                    )
                return Tipo(TipoPrimitivo.BOOL)
            if expr.op in ("&&", "||"):
                if ta.prim not in (TipoPrimitivo.BOOL, TipoPrimitivo.INTEIRO) or \
                   tb.prim not in (TipoPrimitivo.BOOL, TipoPrimitivo.INTEIRO):
                    raise ErroCompilacaoVoidKnee(
                        "Operadores lógicos '&&' e '||' devem ser usados com booleano ou inteiro.",
                        expr.linha,
                        expr.coluna,
                        "semântico",
                    )
                return Tipo(TipoPrimitivo.BOOL)
            raise RuntimeError(f"Operador desconhecido: {expr.op}")
        if isinstance(expr, Call):
            # funções built-in mostraAi/entradaAi tratadas como "quase void"
            if expr.nome == "mostraAi":
                for a in expr.argumentos:
                    self._tipo_expr(a, escopo)
                return Tipo(TipoPrimitivo.VOID)
            if expr.nome == "entradaAi":
                # exigimos referência a variável no primeiro arg?
                for a in expr.argumentos:
                    self._tipo_expr(a, escopo)
                return Tipo(TipoPrimitivo.VOID)
            # funções do usuário
            if expr.nome not in self.funcoes:
                raise ErroCompilacaoVoidKnee(
                    f"Chamada a função desconhecida '{expr.nome}'.",
                    expr.linha,
                    expr.coluna,
                    "semântico",
                )
            ass = self.funcoes[expr.nome]
            if len(expr.argumentos) != len(ass.params):
                raise ErroCompilacaoVoidKnee(
                    f"Função '{expr.nome}' espera {len(ass.params)} argumentos, mas recebeu {len(expr.argumentos)}.",
                    expr.linha,
                    expr.coluna,
                    "semântico",
                )
            for chama_arg, param in zip(expr.argumentos, ass.params):
                t_chama = self._tipo_expr(chama_arg, escopo)
                self._verifica_atribuicao(param.tipo, t_chama, expr.linha, expr.coluna)
            return ass.retorno
        if isinstance(expr, Cast):
            t_expr = self._tipo_expr(expr.expr, escopo)
            # conversões numéricas são permitidas; outras podem dar aviso didático
            if expr.tipo_destino.prim in (
                TipoPrimitivo.INTEIRO,
                TipoPrimitivo.FLUTUANTE,
                TipoPrimitivo.DOBRADURA,
                TipoPrimitivo.BOOL,
            ) and t_expr.prim in (
                TipoPrimitivo.INTEIRO,
                TipoPrimitivo.FLUTUANTE,
                TipoPrimitivo.DOBRADURA,
                TipoPrimitivo.BOOL,
            ):
                return expr.tipo_destino
            # string/char conversão simplificada
            if expr.tipo_destino.prim == TipoPrimitivo.CHAR and t_expr.prim == TipoPrimitivo.INTEIRO:
                return expr.tipo_destino
            raise ErroCompilacaoVoidKnee(
                f"Casting de {t_expr.prim.name} para {expr.tipo_destino.prim.name} não suportado de forma automática.",
                expr.linha,
                expr.coluna,
                "semântico",
            )
        raise RuntimeError(f"Expr desconhecida: {expr!r}")


# =========================================
#  Otimizações simples (O1/O2)
# =========================================

def otimizar_expr(expr: Expr, nivel: str) -> Expr:
    # Constant folding básico
    if isinstance(expr, BinOp):
        expr.esquerda = otimizar_expr(expr.esquerda, nivel)
        expr.direita = otimizar_expr(expr.direita, nivel)
        if isinstance(expr.esquerda, Literal) and isinstance(expr.direita, Literal):
            try:
                if expr.op == "+":
                    val = expr.esquerda.valor + expr.direita.valor
                elif expr.op == "-":
                    val = expr.esquerda.valor - expr.direita.valor
                elif expr.op == "*":
                    val = expr.esquerda.valor * expr.direita.valor
                elif expr.op == "/":
                    val = expr.esquerda.valor / expr.direita.valor
                elif expr.op == "==":
                    val = 1 if expr.esquerda.valor == expr.direita.valor else 0
                elif expr.op == "!=":
                    val = 1 if expr.esquerda.valor != expr.direita.valor else 0
                elif expr.op == "<":
                    val = 1 if expr.esquerda.valor < expr.direita.valor else 0
                elif expr.op == "<=":
                    val = 1 if expr.esquerda.valor <= expr.direita.valor else 0
                elif expr.op == ">":
                    val = 1 if expr.esquerda.valor > expr.direita.valor else 0
                elif expr.op == ">=":
                    val = 1 if expr.esquerda.valor >= expr.direita.valor else 0
                elif expr.op == "&&":
                    val = 1 if (expr.esquerda.valor and expr.direita.valor) else 0
                elif expr.op == "||":
                    val = 1 if (expr.esquerda.valor or expr.direita.valor) else 0
                else:
                    return expr
                # tipo é aproximado como INTEIRO ou FLUTUANTE
                if isinstance(val, float):
                    return Literal(valor=val, tipo=Tipo(TipoPrimitivo.FLUTUANTE), linha=expr.linha, coluna=expr.coluna)
                return Literal(valor=val, tipo=Tipo(TipoPrimitivo.INTEIRO), linha=expr.linha, coluna=expr.coluna)
            except Exception:
                return expr
        return expr
    if isinstance(expr, UnOp):
        expr.expr = otimizar_expr(expr.expr, nivel)
        if isinstance(expr.expr, Literal):
            try:
                if expr.op == "-":
                    val = -expr.expr.valor
                    if isinstance(val, float):
                        return Literal(valor=val, tipo=Tipo(TipoPrimitivo.FLUTUANTE), linha=expr.linha, coluna=expr.coluna)
                    return Literal(valor=val, tipo=expr.expr.tipo, linha=expr.linha, coluna=expr.coluna)
                if expr.op == "!":
                    val = 0 if expr.expr.valor else 1
                    return Literal(valor=val, tipo=Tipo(TipoPrimitivo.BOOL), linha=expr.linha, coluna=expr.coluna)
            except Exception:
                return expr
        return expr
    if isinstance(expr, Cast):
        expr.expr = otimizar_expr(expr.expr, nivel)
        # cast de literal pode ser avaliado
        if isinstance(expr.expr, Literal):
            try:
                if expr.tipo_destino.prim == TipoPrimitivo.INTEIRO:
                    return Literal(valor=int(expr.expr.valor), tipo=Tipo(TipoPrimitivo.INTEIRO), linha=expr.linha, coluna=expr.coluna)
                if expr.tipo_destino.prim == TipoPrimitivo.FLUTUANTE:
                    return Literal(valor=float(expr.expr.valor), tipo=Tipo(TipoPrimitivo.FLUTUANTE), linha=expr.linha, coluna=expr.coluna)
                if expr.tipo_destino.prim == TipoPrimitivo.BOOL:
                    return Literal(valor=1 if expr.expr.valor else 0, tipo=Tipo(TipoPrimitivo.BOOL), linha=expr.linha, coluna=expr.coluna)
            except Exception:
                return expr
        return expr
    if isinstance(expr, Assign):
        expr.expr = otimizar_expr(expr.expr, nivel)
        return expr
    if isinstance(expr, Call):
        expr.argumentos = [otimizar_expr(a, nivel) for a in expr.argumentos]
        return expr
    return expr


def otimizar_stmt(stmt: Stmt, nivel: str) -> Optional[Stmt]:
    """
    Retorna o statement possivelmente transformado,
    ou None se ele puder ser removido (DCE simples em O2).
    """
    if isinstance(stmt, VarDecl):
        if stmt.init is not None:
            stmt.init = otimizar_expr(stmt.init, nivel)
        return stmt
    if isinstance(stmt, ExprStmt):
        stmt.expr = otimizar_expr(stmt.expr, nivel)
        # em O2: eliminar expressões puras que são literais
        if nivel == "O2" and isinstance(stmt.expr, Literal):
            return None
        return stmt
    if isinstance(stmt, ReturnStmt):
        if stmt.expr is not None:
            stmt.expr = otimizar_expr(stmt.expr, nivel)
        return stmt
    if isinstance(stmt, IfStmt):
        stmt.cond = otimizar_expr(stmt.cond, nivel)
        stmt.entao = otimizar_block(stmt.entao, nivel)
        if stmt.senao is not None:
            stmt.senao = otimizar_block(stmt.senao, nivel)
        # em O2: se condição é literal, escolhe ramo
        if nivel == "O2" and isinstance(stmt.cond, Literal):
            if stmt.cond.valor:
                return stmt.entao
            elif stmt.senao is not None:
                return stmt.senao
            return None
        return stmt
    if isinstance(stmt, WhileStmt):
        stmt.cond = otimizar_expr(stmt.cond, nivel)
        stmt.corpo = otimizar_block(stmt.corpo, nivel)
        # não removemos loop mesmo se condição for literal (para não "otimizar demais")
        return stmt
    if isinstance(stmt, ForStmt):
        if stmt.init:
            stmt.init = otimizar_stmt(stmt.init, nivel) or stmt.init
        if stmt.cond:
            stmt.cond = otimizar_expr(stmt.cond, nivel)
        if stmt.passo:
            stmt.passo = otimizar_expr(stmt.passo, nivel)
        stmt.corpo = otimizar_block(stmt.corpo, nivel)
        return stmt
    if isinstance(stmt, Block):
        return otimizar_block(stmt, nivel)
    return stmt


def otimizar_block(bloco: Block, nivel: str) -> Block:
    stmts_novos: List[Stmt] = []
    for s in bloco.stmts:
        s2 = otimizar_stmt(s, nivel)
        if s2 is None:
            continue
        if isinstance(s2, Block):
            # "flatten"
            stmts_novos.extend(s2.stmts)
        else:
            stmts_novos.append(s2)
    bloco.stmts = stmts_novos
    return bloco


def otimizar_programa(prog: Programa, nivel: str) -> Programa:
    if nivel not in ("O0", "O1", "O2"):
        nivel = "O0"
    if nivel == "O0":
        return prog
    for g in prog.globais:
        if g.init is not None:
            g.init = otimizar_expr(g.init, nivel)
    for f in prog.funcoes:
        f.corpo = otimizar_block(f.corpo, nivel)
    return prog


# =========================================
#  Geração de C
# =========================================

class GeradorC:
    def __init__(self, prog: Programa):
        self.prog = prog
        self.linhas: List[str] = []

    def _escape_c_string(self, s: str) -> str:
        """Escapa string para literal C, preservando \n, \t etc.

        - Primeiro converte sequências VoidKnee como \\n, \\t em caracteres reais.
        - Depois reescapa tudo para forma válida em C.
        """
        # converte sequências textuais (\n, \t, ...) em caracteres reais
        s = s.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r').replace('\\0', '\0')
        # escapa barra invertida e aspas
        s = s.replace('\\', '\\\\').replace('"', '\\"')
        # reescapa quebras e outros controles
        s = s.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r').replace('\0', '\\0')
        return s


    def gerar(self) -> str:
        self.linhas.append("#include <stdio.h>")
        self.linhas.append("#include <locale.h>")
        self.linhas.append("")
        self.linhas.append("/* Funções auxiliares para VoidKnee V3 */")
        self.linhas.append("")
        # globais
        for g in self.prog.globais:
            decl = f"{tipo_c(g.tipo)} {g.nome};"
            self.linhas.append(decl)
        if self.prog.globais:
            self.linhas.append("")

        # protótipos de funções
        for f in self.prog.funcoes:
            params = ", ".join(f"{tipo_c(p.tipo)} {p.nome}" for p in f.params)
            self.linhas.append(f"{tipo_c(f.tipo_retorno)} {f.nome}({params});")
        if self.prog.funcoes:
            self.linhas.append("")

        # funções
        for f in self.prog.funcoes:
            self._emit_funcao(f)

        # ponto de entrada: se existir inteirao principal(), gera um main em C
        if any(f.nome == "principal" and f.tipo_retorno.prim == TipoPrimitivo.INTEIRO for f in self.prog.funcoes):
            self.linhas.append("int main(void) {")
            self.linhas.append("    return principal();")
            self.linhas.append("}")
            self.linhas.append("")

        return "\n".join(self.linhas)

    def _emit_funcao(self, f: FuncDecl):
        params = ", ".join(f"{tipo_c(p.tipo)} {p.nome}" for p in f.params)
        self.linhas.append(f"{tipo_c(f.tipo_retorno)} {f.nome}({params})" + " {")
        if f.nome == "principal":
            self.linhas.append("    setlocale(LC_ALL, \"\");")
        self._emit_bloco(f.corpo, indent=1)
        # garantir retorno em funções inteiras se faltou
        if f.tipo_retorno.prim == TipoPrimitivo.INTEIRO and not any(isinstance(s, ReturnStmt) for s in f.corpo.stmts):
            self.linhas.append("    return 0;")
        self.linhas.append("}")
        self.linhas.append("")

    def _emit_bloco(self, bloco: Block, indent: int):
        for s in bloco.stmts:
            self._emit_stmt(s, indent)

    def _emit_stmt(self, stmt: Stmt, indent: int):
        ind = "    " * indent
        if isinstance(stmt, VarDecl):
            if stmt.init:
                expr_c = self._emit_expr(stmt.init)
                self.linhas.append(f"{ind}{tipo_c(stmt.tipo)} {stmt.nome} = {expr_c};")
            else:
                self.linhas.append(f"{ind}{tipo_c(stmt.tipo)} {stmt.nome};")
            return
        if isinstance(stmt, ExprStmt):
            self.linhas.append(f"{ind}{self._emit_expr(stmt.expr)};")
            return
        if isinstance(stmt, ReturnStmt):
            if stmt.expr:
                self.linhas.append(f"{ind}return {self._emit_expr(stmt.expr)};")
            else:
                self.linhas.append(f"{ind}return;")
            return
        if isinstance(stmt, IfStmt):
            cond_c = self._emit_expr(stmt.cond)
            self.linhas.append(f"{ind}if ({cond_c}) " + "{")
            self._emit_bloco(stmt.entao, indent + 1)
            self.linhas.append(f"{ind}" + "}")
            if stmt.senao:
                self.linhas.append(f"{ind}else " + "{")
                self._emit_bloco(stmt.senao, indent + 1)
                self.linhas.append(f"{ind}" + "}")
            return
        if isinstance(stmt, WhileStmt):
            cond_c = self._emit_expr(stmt.cond)
            self.linhas.append(f"{ind}while ({cond_c}) " + "{")
            self._emit_bloco(stmt.corpo, indent + 1)
            self.linhas.append(f"{ind}" + "}")
            return
        if isinstance(stmt, ForStmt):
            # convertemos pra for C padrão, se conseguirmos
            init_c = ""
            if isinstance(stmt.init, VarDecl):
                tipo_str = tipo_c(stmt.init.tipo)
                if stmt.init.init:
                    init_c = f"{tipo_str} {stmt.init.nome} = {self._emit_expr(stmt.init.init)}"
                else:
                    init_c = f"{tipo_str} {stmt.init.nome}"
            elif isinstance(stmt.init, ExprStmt):
                init_c = self._emit_expr(stmt.init.expr)
            cond_c = self._emit_expr(stmt.cond) if stmt.cond else ""
            passo_c = self._emit_expr(stmt.passo) if stmt.passo else ""
            self.linhas.append(f"{ind}for ({init_c}; {cond_c}; {passo_c}) " + "{")
            self._emit_bloco(stmt.corpo, indent + 1)
            self.linhas.append(f"{ind}" + "}")
            return
        if isinstance(stmt, Block):
            self.linhas.append(ind + "{")
            self._emit_bloco(stmt, indent + 1)
            self.linhas.append(ind + "}")
            return
        raise RuntimeError(f"Stmt desconhecido na geração de C: {stmt!r}")

    def _emit_expr(self, expr: Expr) -> str:
        if isinstance(expr, Literal):
            if expr.tipo.prim == TipoPrimitivo.STRING:
                s = self._escape_c_string(expr.valor)
                return f"\"{s}\""
            if expr.tipo.prim == TipoPrimitivo.CHAR:
                return f"'{expr.valor}'"
            if expr.tipo.prim == TipoPrimitivo.FLUTUANTE:
                return f"{expr.valor}f"
            return str(expr.valor)
        if isinstance(expr, VarRef):
            return expr.nome
        if isinstance(expr, Assign):
            return f"{expr.nome} = {self._emit_expr(expr.expr)}"
        if isinstance(expr, UnOp):
            return f"({expr.op}{self._emit_expr(expr.expr)})"
        if isinstance(expr, BinOp):
            return f"({self._emit_expr(expr.esquerda)} {expr.op} {self._emit_expr(expr.direita)})"
        if isinstance(expr, Cast):
            return f"(({tipo_c(expr.tipo_destino)}) {self._emit_expr(expr.expr)})"
        if isinstance(expr, Call):
            # trata mostraAi/entradaAi como wrappers em C
            if expr.nome == "mostraAi":
                # estratégia simples: se primeiro arg é string literal, usa diretamente
                if expr.argumentos and isinstance(expr.argumentos[0], Literal) and \
                   expr.argumentos[0].tipo.prim == TipoPrimitivo.STRING:
                    fmt = self._escape_c_string(expr.argumentos[0].valor)
                    outros = expr.argumentos[1:]
                    if outros:
                        args = ", ".join(self._emit_expr(a) for a in outros)
                        return f"printf(\"%s\", \"{fmt}\"); /* simplificado */ printf(\"\", {args})"
                    else:
                        return f"printf(\"%s\", \"{fmt}\")"
                else:
                    # fallback
                    inner = ", ".join(self._emit_expr(a) for a in expr.argumentos)
                    return f"printf(\"[mostraAi simplificado] %d\\n\", {inner})"
            if expr.nome == "entradaAi":
                # placeholder simples: lê int no primeiro argumento
                if len(expr.argumentos) != 1 or not isinstance(expr.argumentos[0], VarRef):
                    return "/* entradaAi mal utilizada */"
                nome = expr.argumentos[0].nome
                return f"scanf(\"%d\", &{nome})"
            args = ", ".join(self._emit_expr(a) for a in expr.argumentos)
            return f"{expr.nome}({args})"
        raise RuntimeError(f"Expr desconhecida na geração de C: {expr!r}")


# =========================================
#  Geração de "assembly" de máquina de pilha
# =========================================

class GeradorAssembly:
    """
    Backend didático: gera um assembly fictício de máquina de pilha.

    Exemplo de instruções:
      PUSH 3
      LOAD x
      ADD
      JMP label
      JZ label
      CALL f
      RET
    """

    def __init__(self, prog: Programa):
        self.prog = prog
        self.linhas: List[str] = []

    def gerar(self) -> str:
        self.linhas.append("; Assembly VoidKnee V3 - máquina de pilha didática")
        self.linhas.append("; Este backend é conceitual e não é montado por um assembler real.")
        self.linhas.append("")

        for g in self.prog.globais:
            self.linhas.append(f"; global {g.nome} : {g.tipo.prim.name}")
        if self.prog.globais:
            self.linhas.append("")

        for f in self.prog.funcoes:
            self._emit_func(f)

        return "\n".join(self.linhas)

    def _emit_func(self, f: FuncDecl):
        self.linhas.append(f"{f.nome}:")
        self.linhas.append("    ; prólogo (simples)")
        self._emit_block(f.corpo, indent="    ")
        if f.tipo_retorno.prim == TipoPrimitivo.INTEIRO:
            self.linhas.append("    PUSH 0 ; retorno padrão caso não haja 'retorna'")
        self.linhas.append("    RET")
        self.linhas.append("")

    def _emit_block(self, bloco: Block, indent: str):
        for s in bloco.stmts:
            self._emit_stmt(s, indent)

    def _emit_stmt(self, stmt: Stmt, indent: str):
        if isinstance(stmt, VarDecl):
            # sem alocação real, apenas comentário
            self.linhas.append(f"{indent}; var {stmt.nome} : {stmt.tipo.prim.name}")
            if stmt.init:
                self._emit_expr(stmt.init, indent)
                self.linhas.append(f"{indent}STORE {stmt.nome}")
            return
        if isinstance(stmt, ExprStmt):
            self._emit_expr(stmt.expr, indent)
            # descarrega topo da pilha para não acumular lixo
            self.linhas.append(f"{indent}POP")
            return
        if isinstance(stmt, ReturnStmt):
            if stmt.expr:
                self._emit_expr(stmt.expr, indent)
            else:
                self.linhas.append(f"{indent}PUSH 0")
            self.linhas.append(f"{indent}RET")
            return
        if isinstance(stmt, IfStmt):
            lbl_else = self._novo_rotulo("else")
            lbl_end = self._novo_rotulo("endif")
            self._emit_expr(stmt.cond, indent)
            self.linhas.append(f"{indent}JZ {lbl_else}")
            self._emit_block(stmt.entao, indent)
            self.linhas.append(f"{indent}JMP {lbl_end}")
            self.linhas.append(f"{lbl_else}:")
            if stmt.senao:
                self._emit_block(stmt.senao, indent)
            self.linhas.append(f"{lbl_end}:")
            return
        if isinstance(stmt, WhileStmt):
            lbl_ini = self._novo_rotulo("while")
            lbl_end = self._novo_rotulo("endwhile")
            self.linhas.append(f"{lbl_ini}:")
            self._emit_expr(stmt.cond, indent)
            self.linhas.append(f"{indent}JZ {lbl_end}")
            self._emit_block(stmt.corpo, indent)
            self.linhas.append(f"{indent}JMP {lbl_ini}")
            self.linhas.append(f"{lbl_end}:")
            return
        if isinstance(stmt, ForStmt):
            # for simples: traduz para while
            if stmt.init:
                self._emit_stmt(stmt.init, indent)
            lbl_ini = self._novo_rotulo("for")
            lbl_end = self._novo_rotulo("endfor")
            self.linhas.append(f"{lbl_ini}:")
            if stmt.cond:
                self._emit_expr(stmt.cond, indent)
                self.linhas.append(f"{indent}JZ {lbl_end}")
            self._emit_block(stmt.corpo, indent)
            if stmt.passo:
                self._emit_expr(stmt.passo, indent)
                self.linhas.append(f"{indent}POP")
            self.linhas.append(f"{indent}JMP {lbl_ini}")
            self.linhas.append(f"{lbl_end}:")
            return
        if isinstance(stmt, Block):
            self._emit_block(stmt, indent)
            return

    _contador_rotulos = 0

    def _novo_rotulo(self, base: str) -> str:
        GeradorAssembly._contador_rotulos += 1
        return f"{base}_{GeradorAssembly._contador_rotulos}"

    def _emit_expr(self, expr: Expr, indent: str):
        if isinstance(expr, Literal):
            self.linhas.append(f"{indent}PUSH {expr.valor}")
            return
        if isinstance(expr, VarRef):
            self.linhas.append(f"{indent}LOAD {expr.nome}")
            return
        if isinstance(expr, Assign):
            self._emit_expr(expr.expr, indent)
            self.linhas.append(f"{indent}STORE {expr.nome}")
            self.linhas.append(f"{indent}LOAD {expr.nome}")
            return
        if isinstance(expr, UnOp):
            self._emit_expr(expr.expr, indent)
            if expr.op == "-":
                self.linhas.append(f"{indent}NEG")
            if expr.op == "!":
                self.linhas.append(f"{indent}NOT")
            return
        if isinstance(expr, BinOp):
            self._emit_expr(expr.esquerda, indent)
            self._emit_expr(expr.direita, indent)
            opmap = {
                "+": "ADD",
                "-": "SUB",
                "*": "MUL",
                "/": "DIV",
                "==": "EQ",
                "!=": "NEQ",
                "<": "LT",
                "<=": "LE",
                ">": "GT",
                ">=": "GE",
                "&&": "AND",
                "||": "OR",
            }
            self.linhas.append(f"{indent}{opmap.get(expr.op, 'NOP')}")
            return
        if isinstance(expr, Cast):
            self._emit_expr(expr.expr, indent)
            self.linhas.append(f"{indent}; CAST para {expr.tipo_destino.prim.name}")
            return
        if isinstance(expr, Call):
            # built-ins
            if expr.nome == "mostraAi":
                for a in expr.argumentos:
                    self._emit_expr(a, indent)
                    self.linhas.append(f"{indent}CALL BUILTIN_PRINT")
                    self.linhas.append(f"{indent}POP")
                self.linhas.append(f"{indent}PUSH 0")
                return
            if expr.nome == "entradaAi":
                self.linhas.append(f"{indent}; entradaAi não implementado no assembly didático")
                self.linhas.append(f"{indent}PUSH 0")
                return
            # chamada normal
            for a in expr.argumentos:
                self._emit_expr(a, indent)
            self.linhas.append(f"{indent}CALL {expr.nome}")
            return


# =========================================
#  API pública
# =========================================

def traduzir(fonte: str, *, backend: str = "c", otimizacao: str = "O0") -> str:
    """
    Compila código VoidKnee V3 para C ou assembly didático.

    backend: "c" (default) ou "asm"
    otimizacao: "O0", "O1" ou "O2"
    """
    lexer = Lexer(fonte)
    tokens = lexer.tokens()
    parser = Parser(tokens)
    prog = parser.parse()

    analise = AnalisadorSemantico(prog)
    analise.analisar()

    prog = otimizar_programa(prog, otimizacao)

    if backend == "asm":
        return GeradorAssembly(prog).gerar()
    return GeradorC(prog).gerar()


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Compilador VoidKnee V3 (didático).")
    ap.add_argument("arquivo", nargs="?", help="Arquivo fonte VoidKnee (.vk). Se omitido, lê stdin.")
    ap.add_argument("-b", "--backend", choices=["c", "asm"], default="c", help="Backend de saída (c ou asm).")
    ap.add_argument("-O", "--otimizacao", choices=["O0", "O1", "O2"], default="O0", help="Nível de otimização.")
    args = ap.parse_args()

    if args.arquivo:
        with open(args.arquivo, "r", encoding="utf-8") as f:
            src = f.read()
    else:
        src = sys.stdin.read()

    try:
        saida = traduzir(src, backend=args.backend, otimizacao=args.otimizacao)
        sys.stdout.write(saida)
    except ErroCompilacaoVoidKnee as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)