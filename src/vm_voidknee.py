
#!/usr/bin/env python3
"""
Máquina de pilha didática para executar o assembly gerado pelo VoidKnee V3.

Uso:
    python vm_voidknee.py caminho_do_arquivo.asm [rotulo_inicial]

Exemplo:
    python vm_voidknee.py src/out/v3_E_fatorial_asm_V3.asm principal
"""

import sys
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any


@dataclass
class Instr:
    op: str
    args: Tuple[str, ...]


class VM:
    def __init__(self, instrs: List[Instr], labels: Dict[str, int], entry: str = "principal"):
        if entry not in labels:
            raise ValueError(f"Rótulo de entrada '{entry}' não encontrado no programa.")
        self.instrs = instrs
        self.labels = labels
        self.ip = labels[entry]          # instruction pointer
        self.stack: List[Any] = []       # evaluation stack
        self.call_stack: List[int] = []  # return addresses
        self.mem: Dict[str, Any] = {}    # memória de variáveis "globais"

    # utilidades de pilha -------------------------------------------------
    def push(self, v: Any):
        self.stack.append(v)

    def pop(self) -> Any:
        if not self.stack:
            raise RuntimeError("Pilha vazia (underflow).")
        return self.stack.pop()

    # execução ------------------------------------------------------------
    def run(self) -> Optional[Any]:
        while 0 <= self.ip < len(self.instrs):
            inst = self.instrs[self.ip]
            self.ip += 1   # avançamos aqui; jumps/chamadas podem sobrescrever

            op = inst.op
            args = inst.args

            if op == "PUSH":
                value = self._parse_number(args[0])
                self.push(value)

            elif op == "LOAD":
                name = args[0]
                self.push(self.mem.get(name, 0))

            elif op == "STORE":
                name = args[0]
                value = self.pop()
                self.mem[name] = value

            elif op == "POP":
                _ = self.pop()

            elif op in ("ADD", "SUB", "MUL", "DIV",
                        "EQ", "NEQ", "LT", "LE", "GT", "GE",
                        "AND", "OR"):
                self._binop(op)

            elif op in ("NEG", "NOT"):
                self._unop(op)

            elif op == "JMP":
                label = args[0]
                self.ip = self._label_ip(label)

            elif op == "JZ":
                label = args[0]
                cond = self.pop()
                if not cond:
                    self.ip = self._label_ip(label)

            elif op == "CALL":
                target = args[0]
                # built-in de debug/IO usado pelo mostraAi
                if target == "BUILTIN_PRINT":
                    value = self.pop()
                    print(value, end="")
                    # retorno fictício
                    self.push(0)
                else:
                    self.call_stack.append(self.ip)
                    self.ip = self._label_ip(target)

            elif op == "RET":
                # valor de retorno (se existir) fica no topo da pilha
                if not self.call_stack:
                    # fim do programa
                    return self.stack[-1] if self.stack else None
                self.ip = self.call_stack.pop()

            elif op == "NOP":
                pass

            else:
                raise RuntimeError(f"Instrução desconhecida: {op} {args}")

        # terminou sem RET
        return self.stack[-1] if self.stack else None

    # helpers -------------------------------------------------------------
    def _label_ip(self, label: str) -> int:
        if label not in self.labels:
            raise RuntimeError(f"Rótulo '{label}' não definido.")
        return self.labels[label]

    def _parse_number(self, s: str) -> Any:
        # tenta inteiro, depois float
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                raise RuntimeError(f"Valor numérico inválido em PUSH: {s!r}")

    def _binop(self, op: str):
        b = self.pop()
        a = self.pop()
        if op == "ADD":
            self.push(a + b)
        elif op == "SUB":
            self.push(a - b)
        elif op == "MUL":
            self.push(a * b)
        elif op == "DIV":
            self.push(a / b)
        elif op == "EQ":
            self.push(1 if a == b else 0)
        elif op == "NEQ":
            self.push(1 if a != b else 0)
        elif op == "LT":
            self.push(1 if a < b else 0)
        elif op == "LE":
            self.push(1 if a <= b else 0)
        elif op == "GT":
            self.push(1 if a > b else 0)
        elif op == "GE":
            self.push(1 if a >= b else 0)
        elif op == "AND":
            self.push(1 if (a and b) else 0)
        elif op == "OR":
            self.push(1 if (a or b) else 0)

    def _unop(self, op: str):
        v = self.pop()
        if op == "NEG":
            self.push(-v)
        elif op == "NOT":
            self.push(0 if v else 1)


# -------------------------------------------------------------------------
# Parser de arquivo .asm gerado pelo VoidKnee
# -------------------------------------------------------------------------

def carregar_arquivo(path: str) -> Tuple[List[Instr], Dict[str, int]]:
    instrs: List[Instr] = []
    labels: Dict[str, int] = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.rstrip()

            # remove comentários começando com ';'
            code = raw.split(";", 1)[0].strip()
            if not code:
                continue

            # rótulo 'algo:'
            if code.endswith(":"):
                label = code[:-1].strip()
                labels[label] = len(instrs)
                continue

            parts = code.split()
            op = parts[0].upper()
            args = tuple(parts[1:])
            instrs.append(Instr(op=op, args=args))

    return instrs, labels


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print("Uso: python vm_voidknee.py arquivo.asm [rotulo_inicial]")
        return 1

    path = argv[0]
    entry = argv[1] if len(argv) > 1 else "principal"

    instrs, labels = carregar_arquivo(path)
    vm = VM(instrs, labels, entry=entry)
    result = vm.run()

    print("\n\n== Execução terminada ==")
    print("Topo da pilha:", result)
    print("Memória:", vm.mem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
