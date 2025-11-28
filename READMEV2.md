# VoidKnee 🦵 → C (README • V2)

Projeto da disciplina **Compiladores**. A **VoidKnee** é uma linguagem didática que traduz para **C** através de um pipeline completo:

**Léxico → Parser/AST → Semântica → Geração de C**.

---

## 🚀 Novidades da V2
- **Fluxo de controle estável**: `sejoelho/outracoisa`, `enquantoDoi`, `praCada`.
- **Tipos numéricos + booleano**: `inteirao`, `flutuante`, `dobradura`, `dorzinha (char)`, `verdadeQueDoi (bool)` com promoções coerentes.
- **Booleano em aritmética** (0/1) e em concatenação de strings.
- **Strings** (`dorzona` = `char[N]`) com **leitura segura**: `"%Ns"` e *null-terminator* garantido.
- **Leitura de `char`** robusta com `" %c"` (consome `\n` pendente).
- **Vetores e matrizes**: declaração, indexação n-dimensional e uso em I/O.
- **C gerado** com `u8"..."` e `setlocale(LC_ALL,"")` para facilitar acentuação.

---

## 📦 Estrutura de pastas (projeto)
```
voidknee/
├─ src/
│  ├─ compiler/                         # código do compilador
│  │  ├─ voidknee_compiladorV1.py
│  │  └─ voidknee_compiladorV2.py
│  ├─ notebooks/                        # apresentações/demos
│  │  ├─ voidkneeV1.ipynb
│  │  └─ voidkneeV2.ipynb
│  └─ out/                              # .c gerados pelos notebooks (gitignored)
├─ out/                                 # (opcional) saída alternativa
├─ LICENSE
└─ README.md
```

> Por padrão os exemplos do notebook salvam em **`src/out/`**. Pode ajustar para `./out/` se preferir.

---

## ✅ Requisitos
- **Python 3.10+**
- **GCC** no PATH  
  - Windows: MinGW‑w64 / MSYS2 / WinLibs  
  - macOS: Xcode Command Line Tools  
  - Linux: build‑essential

Verifique:
```bash
python --version
gcc --version
```

---

## 🧪 Usando com **Jupyter/VS Code** (recomendado)
No topo do `src/notebooks/voidkneeV2.ipynb`, use uma **célula de setup** para garantir os caminhos e um helper para salvar os `.c` em `src/out/`:

```python
# ⚙️ Setup para estrutura: .../voidknee/src/{compiler, notebooks, out}
import sys
from pathlib import Path

NB_DIR = Path.cwd()
SRC = NB_DIR.parent if NB_DIR.name == "notebooks" else NB_DIR   # -> .../src
OUT = SRC / "out"
OUT.mkdir(parents=True, exist_ok=True)

# Importa o compilador V2
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from compiler.voidknee_compiladorV2 import traduzir

# Helper: gera .c em src/out
def gerar_c(nome: str, fonte_vk: str) -> str:
    c_code = traduzir(fonte_vk)
    destino = OUT / f"{nome}.c"
    destino.write_text(c_code, encoding="utf-8")
    print(f"✅ Gerado: {destino.resolve()}")
    return c_code
```

Depois, para cada exemplo:
```python
source = '''
inteirao x;
x = 3;
enquantoDoi (x > 0) {
    mostraAi("x = " + x + "\n");
    x = x - 1;
}
'''
c_code = gerar_c("exemplo_while", source)
print(c_code)
```

---

## 🖥️ Compilando e executando o **C** gerado
No terminal (na raiz do projeto):
```bash
gcc src/out/exemplo_while.c -O2 -o src/out/exemplo_while
./src/out/exemplo_while             # Linux/macOS
src\out\exemplo_while.exe         # Windows
```

Se preferir, configure o VS Code com um `tasks.json` para compilar o arquivo ativo gerando um `.exe` com o **mesmo nome do `.c`**:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "C/C++: build active file (gcc)",
      "type": "shell",
      "command": "gcc",
      "args": ["-O2", "${file}", "-o", "${fileDirname}/${fileBasenameNoExtension}"],
      "group": { "kind": "build", "isDefault": true },
      "problemMatcher": ["$gcc"]
    }
  ]
}
```

---

## ⚙️ Como o compilador funciona (resumo operacional)
- **`traduzir(fonte: str) -> str`** encadeia as fases: léxico → parser/AST → semântica → **geração de C**.
- **Léxico**: reconhece palavras‑chave, identificadores, números, strings (`"..."` com escapes), operadores e pontuação.
- **Parser/AST**: constrói nós para declarações, comandos (`sejoelho`, `enquantoDoi`, `praCada`, `mostraAi`, `entradaAi`), expressões, vetores/matrizes e acessos com `[]`.
- **Semântica**: valida **uso antes da declaração**, **redeclaração**, **índices compatíveis** em arrays/matrizes, **coerções** (`int < float < double`) e booleano (`int` 0/1).
- **Geração de C**:
  - inclui `<stdio.h>`, `<string.h>`, `<locale.h>` e usa `setlocale(LC_ALL,"")`;
  - **`mostraAi`** → constrói `printf` com formato e lista de argumentos; strings como `%s`;
  - **`entradaAi`** → `scanf` com especificador por tipo; **string** usa `%Ns`; **char** usa `" %c"`;
  - declarações sobem para o início de `main`; controle de fluxo mapeia 1:1 para `if/else`, `while`, `for`.

Para detalhes linha‑a‑linha do pipeline com trechos reais do código, consulte o arquivo **“voidknee_compilador_passos_com_trechos.md”**.

---

## 🧯 Erros comuns e dicas
- **“Variável 'j' redeclarada”** em laços aninhados: declare `inteirao j;` **uma vez** fora do primeiro laço e apenas reutilize dentro.
- **Leitura de `char` capturando `\n`**: o compilador já usa `" %c"`; evite ler `char` imediatamente após `scanf` de números sem consumir o `\n`.
- **Strings curtas cortadas**: aumente o tamanho do `char[N]` (ex.: `dorzona nome[32];`) — a leitura usa `%Ns` (N−1 útil).
- **Acentos/UTF‑8** no Windows: confirme o *Code Page* do terminal ou rode no VS Code. O C usa `u8"..."` + `setlocale`.

---

## 🧭 Roadmap curto
- Funções de usuário (declaração/chamada/retorno).
- Escopos por bloco e sombreamento seguro.
- Melhorias de diagnósticos (spans linha/coluna).
- Backend alternativo (WASM) mantendo a mesma AST.

---

## 📜 Licença
Este projeto é distribuído sob a licença indicada no arquivo **LICENSE**.

