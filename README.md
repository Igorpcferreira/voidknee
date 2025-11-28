# VoidKnee 🦵 – Linguagem de Brinquedo para Compiladores

Projeto da disciplina **Compiladores** (PUC Goiás).  
A **VoidKnee** é uma linguagem de programação de brinquedo – bem-humorada e cheia de piadas com joelho – usada como laboratório para estudar **implementação de compiladores de ponta a ponta**.

Ao longo do projeto criamos três versões principais da linguagem e do compilador:

- **V1** – primeiro compilador funcional, com léxico, parser, AST, análise semântica básica e geração de C.  
- **V2** – versão mais madura, com fluxo de controle estável, tipos numéricos/booleano mais completos, vetores/matrizes, strings melhoradas e I/O robusta.  
- **V3** – nível “hardcore didático”: funções, recursão, casting explícito, erros didáticos, otimizações (**O0/O1/O2**) e backend alternativo em **assembly de máquina de pilha**, com uma **VM em Python** para executar esse assembly.

Este README é o **guia geral do projeto**.  
Os detalhes específicos de cada versão estão em:

- `docs/READMEV1.md` – foco na primeira versão;  
- `docs/READMEV2.md` – evolução para V2;  
- `READMEV3.md` – detalhes aprofundados da V3 (funções, casting, otimização, assembly).

---

## 😄 Por que “VoidKnee”?

Homenagem bem-humorada ao **joelho cansado** do Igor.  
O nome “VoidKnee” (algo como *“joelho vazio”*) virou piada interna, que:

- Deixa o projeto mais leve e lembrável;
- Gera mensagens e exemplos com trocadilhos de dor no joelho;
- Ajuda a fixar um assunto que normalmente parece “pesado” (compiladores).

---

## 🎯 Objetivos didáticos

- Implementar um **compilador completo** para uma linguagem própria:
  - Léxico → Parser → AST → Análise Semântica → Geração de Código;
- Mostrar na prática como uma linguagem de alto nível pode ser mapeada para **C**;
- Evoluir o compilador em versões (V1, V2, V3), reforçando:
  - **Design de linguagem** (tipos, controle, I/O, funções);
  - **Organização de código** (módulos, classes, AST, visitors);
  - **Diagnósticos** (erros amigáveis, linha/coluna, mensagens didáticas);
  - **Backends** diferentes (C, “assembly” de pilha);
  - **Otimização** simples na AST (constant folding, remoção de código morto).

---

## 🧱 Visão geral da arquitetura

Todas as versões seguem um pipeline clássico:

```text
Fonte (.vk)
  → Léxico        (tokens)
  → Parser        (AST)
  → Semântica     (tipos, escopos, checagens)
  → Otimizador    (apenas na V3, O0/O1/O2)
  → Backend       (C ou Assembly didático)
  → gcc / VM      (executável nativo ou execução na máquina de pilha)
```

### Componentes principais

- **Lexer** – converte o texto em uma sequência de tokens (identificadores, palavras-chave, números, strings, operadores, pontuação).
- **Parser** – constrói a **AST** (árvore sintática abstrata) usando funções recursivas para expressões, comandos, blocos, etc.
- **AST** – tipos Python (`@dataclass`) representando programa, funções, declarações, expressões, comandos, etc.
- **Analisador semântico** – faz:
  - tabela de símbolos (variáveis, funções);
  - checagem de tipos em expressões e atribuições;
  - verificação de escopos, duplicação de nomes, retorno em funções, etc.
- **Otimizador (V3)** – recebe a AST e aplica transformações simples:
  - *constant folding*;
  - eliminação de condicionais triviais;
  - remoção de statements mortos.
- **Geradores de código**:
  - `GeradorC` – gera C legível e compilável com `gcc`;
  - `GeradorAssembly` (V3) – gera assembly de **máquina de pilha fictícia**.
- **VM (V3)** – `vm_voidknee.py`, interpretador para o assembly gerado, usado em demonstrações.

---

## 📜 Evolução por versões

### V1 – VoidKnee → C (primeiro compilador)

Foco:

- Pipeline completo minimalista;
- Sintaxe básica, operadores, condicionais, laços, I/O.

Principais características:

- Tipos primitivos:
  - `inteirao` → `int`
  - `flutuante` → `float`
  - `dobradura` → `double`
  - `verdadeQueDoi` → `int` (0/1)
- Controle de fluxo:
  - `sejoelho (cond) { ... } outracoisa { ... }` → `if (cond) { ... } else { ... }`
  - `enquantoDoi (cond) { ... }` → `while (cond) { ... }`
  - `praCada (init; cond; passo) { ... }` → `for (init; cond; passo) { ... }`
- I/O:
  - `mostraAi(expr1, expr2, ...)` → `printf(...)` (concatenação via `+` na AST)
  - `entradaAi(x)` → `scanf("%d" | "%f" | "%lf", &x)` dependendo do tipo
- Booleanos:
  - literais `verdadeiro` / `falso` → `1` / `0`
  - operadores lógicos mapeados para `&&`, `||`, `!`
- Organização:
  - projeto em Python, com CLI simples que recebe um `.vk` e gera `.c`;
  - exemplos básicos demonstrando condicionais e laços.

V1 foi a base para tudo: depois que a pipeline principal estava estável, começamos a aumentar a linguagem.

---

### V2 – VoidKnee → C com tipos e I/O mais ricos

A V2 é documentada em `docs/READMEV2.md` e refinou bastante a linguagem e a geração de C.

Destaques da V2:

- **Fluxo de controle consolidado**:
  - `sejoelho/outracoisa`, `enquantoDoi`, `praCada` totalmente suportados;
  - blocos com escopo de variáveis.

- **Tipos numéricos e booleano mais completos**:
  - `inteirao`, `flutuante`, `dobradura`, `dorzinha` (char), `verdadeQueDoi` (bool);
  - promoções coerentes (ex.: int + double → double).

- **Strings e arrays**:
  - `dorzona` como `char[N]` simples;
  - suporte a vetores e matrizes (declaração, indexação n-dimensional);
  - uso de vetores/matrizes em I/O (`mostraAi` e `entradaAi`).

- **I/O mais robusta**:
  - leitura de `char` usando `" %c"` para consumir `
` pendente;
  - leitura de strings com `"%Ns"` e *null-terminator* garantido.

- **C gerado mais amigável**:
  - uso de `u8"..."` quando necessário;
  - `setlocale(LC_ALL,"")` para facilitar acentuação no Windows.

Esses avanços tornaram a VoidKnee mais próxima de uma mini-linguagem imperativa com arrays e strings, ainda sem funções de usuário.

---

### V3 – Funções, recursão, casting, otimização e assembly

A V3 é a versão mais completa, documentada em detalhes em `READMEV3.md`.

Novidades em relação à V2:

1. **Funções de usuário e recursão**
   - Declaração semelhante a C:
     ```voidknee
     inteirao fatorial(inteirao n) {
         sejoelho (n <= 1) {
             retorna 1;
         } outracoisa {
             retorna n * fatorial(n - 1);
         }
     }

     inteirao principal() {
         retorna fatorial(5);
     }
     ```
   - Ponto de entrada obrigatório: `inteirao principal()`;
   - O C gerado inclui:
     ```c
     int main(void) {
         return principal();
     }
     ```

2. **Casting explícito**
   - Sintaxe C-like:
     ```voidknee
     inteirao x;
     flutuante y;
     dobradura z;

     y = 3.5;
     z = (dobradura) y * 2;
     x = (inteirao) z;
     ```
   - Casting representado na AST (`Cast`) e respeitado na geração de C.

3. **Erros didáticos**
   - Uso de uma exceção única: `ErroCompilacaoVoidKnee`.
   - Cada erro inclui:
     - etapa (`"léxico"`, `"sintático"`, `"semântico"`);
     - linha e coluna;
     - mensagem amigável, frequentemente com dica, por exemplo:
       > Não é possível atribuir valor do tipo DORZONA em variável do tipo INTEIRO.  
       > Dica: use um casting explícito, ex.: `(inteirao) ...`.

4. **Níveis de otimização – O0 / O1 / O2**
   - `O0`: pipeline sem otimização (só checagens).
   - `O1`: *constant folding* em expressões:
     - `2 + 3 * 4` → `14`
     - `1 && 0` → `0`
   - `O2`: herda O1 e simplifica controle de fluxo trivial:
     - `sejoelho (0) { blocoA }` some;
     - `sejoelho (1) { blocoA } outracoisa { blocoB }` vira apenas `blocoA`.

5. **Backend alternativo em assembly de pilha**
   - Classe `GeradorAssembly` gera um assembly de máquina de pilha fictícia, com instruções como:
     - `PUSH`, `POP`
     - `LOAD`, `STORE`
     - `ADD`, `SUB`, `MUL`, `DIV`
     - `EQ`, `NEQ`, `LT`, `LE`, `GT`, `GE`
     - `AND`, `OR`, `NEG`, `NOT`
     - `JMP`, `JZ`
     - `CALL`, `RET`
   - Cada função se torna um rótulo (`fatorial:`, `principal:`).

6. **VM em Python (`vm_voidknee.py`)**
   - Interpretador da máquina de pilha para executar o assembly gerado.
   - Exemplo de uso:
     ```bash
     py src/vm_voidknee.py src/out/v3_E_fatorial_asm_V3.asm principal
     ```
   - A VM:
     - Carrega as instruções do `.asm`;
     - Começa em `principal`;
     - Executa instruções de pilha;
     - Ao final, imprime o topo da pilha e o conteúdo da “memória” (variáveis).

---

## 🔑 Vocabulário da linguagem (consolidado)

### Tipos

| VoidKnee        | Significado       | C (backend)   |
|-----------------|-------------------|--------------|
| `inteirao`      | inteiro           | `int`        |
| `flutuante`     | ponto flutuante   | `float`      |
| `dobradura`     | dupla precisão    | `double`     |
| `verdadeQueDoi` | booleano (0/1)    | `int`        |
| `dorzinha`      | caractere         | `char`       |
| `dorzona`       | string (V2/V3)    | `char*` ou `char[N]` (dependendo da versão) |

### Controle de fluxo

- `sejoelho (cond) { ... } outracoisa { ... }` → `if / else`
- `enquantoDoi (cond) { ... }` → `while`
- `praCada (init; cond; passo) { ... }` → `for`

### Entrada e saída

- `mostraAi(expr1, expr2, ...)` → `printf(...)`  
  concatenação feita na AST.
- `entradaAi(x)` → `scanf(...)` apropriado para o tipo.

### Booleanos

- Literais: `verdadeiro`, `falso` → `1`, `0`.
- Operadores lógicos: `&&`, `||`, `!`.

### Comentários

- `// texto` – comentário de linha.
- `/* ... */` – comentário de bloco.
- Em algumas versões existe comentário “especial” `/// texto`, mapeado para blocos no C.

---

## 📂 Estrutura de diretórios (sugerida)

```text
voidknee/
  src/
    compiler/
      voidknee_compiladorV1.py
      voidknee_compiladorV2.py
      voidknee_compiladorV3.py
    notebooks/
      voidkneeV1.ipynb
      voidkneeV2.ipynb
      voidkneeV3.ipynb
    out/
      ... arquivos .c e .asm gerados ...
  vm_voidknee.py
  docs/
    READMEV1.md
    READMEV2.md
  READMEV3.md
  README.md            # este README geral
  LICENSE
```

---

## ▶️ Como rodar (C backend)

Pré-requisitos:

- **Python 3.10+**
- **GCC** (ou compilador C equivalente)

Verifique:

```bash
python --version
gcc --version
```

Uso típico via Python (V2/V3):

```python
from pathlib import Path
import sys

SRC = Path("src")            # ajuste se necessário
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from compiler.voidknee_compiladorV3 import traduzir

codigo_vk = """
inteirao principal() {
    inteirao x;
    x = 2 + 3 * 4;
    mostraAi("Resultado = ");
    mostraAi(x);
    retorna 0;
}
"""

c_code = traduzir(codigo_vk, backend="c", otimizacao="O1")
(Path("src/out") / "exemplo_V3.c").write_text(c_code, encoding="utf-8")
```

Compilando e executando:

```bash
gcc src/out/exemplo_V3.c -o src/out/exemplo_V3.exe
./src/out/exemplo_V3.exe    # Windows: .\src\out\exemplo_V3.exe
```

---

## ▶️ Como rodar o assembly (V3 + VM)

Gerar o `.asm` a partir do mesmo código:

```python
from compiler.voidknee_compiladorV3 import traduzir
from pathlib import Path

codigo_vk = """
inteirao fatorial(inteirao n) {
    sejoelho (n <= 1) {
        retorna 1;
    } outracoisa {
        retorna n * fatorial(n - 1);
    }
}

inteirao principal() {
    inteirao x;
    x = 5;
    retorna fatorial(x);
}
"""

asm = traduzir(codigo_vk, backend="asm", otimizacao="O1")
(Path("src/out") / "fatorial_V3.asm").write_text(asm, encoding="utf-8")
```

Executar na VM (a partir da raiz do projeto):

```bash
py src/vm_voidknee.py src/out/fatorial_V3.asm principal
```

Saída esperada (exemplo):

```text
== Execução terminada ==
Topo da pilha: 120
Memória: {"x": 5}
```

---

## 🤹‍♂️ Brincadeiras e estilo do projeto

- O nome **VoidKnee** foi escolhido para brincar com o “joelho” do Igor.
- Palavras-chave fazem trocadilho com dor / joelho:
  - `sejoelho`, `enquantoDoi`, `verdadeQueDoi`, `dorzinha`, `dorzona`…
- Mensagens de erro da V3 são pensadas para aluno, com dicas e texto leve.
- Os notebooks (`voidkneeV1.ipynb`, `voidkneeV2.ipynb`, `voidkneeV3.ipynb`) funcionam como
  **slides vivos** com código, exemplos e pequenas “palmas da plateia” no final.

Tudo isso ajuda a transformar um assunto tradicionalmente pesado (compiladores) em algo mais divertido e acessível.

---

## 🧭 Roadmap do projeto

Algumas ideias futuras:

- Expor flags para imprimir **tokens**, **AST** ou uma **IR** intermediária direto pelo CLI;
- Expandir o backend de assembly para lidar com vetores/matrizes;
- Criar um modo “debug” na VM (passo a passo, inspeção de pilha e memória);
- Explorar um backend alternativo como **WASM** reutilizando a mesma AST;
- Implementar um pequeno **REPL** VoidKnee para testes rápidos em aula.

---

## 📜 Licença

O projeto é distribuído sob a licença especificada no arquivo **LICENSE**.

---

Feito com 🦵 + 💻 + ☕ – e algumas dores de joelho no caminho.  
**VoidKnee: linguagem de brinquedo, aprendizado de verdade.**
