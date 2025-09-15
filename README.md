# VoidKnee 🦵 → C (README)

Projeto da disciplina **Compiladores**.  
A VoidKnee é nossa linguagem de brinquedo com pipeline didático completo:
**Tokens → Parser → AST → Semântica → CodeGen (C)**.

---

## 😄 Por que “VoidKnee”?
Homenagem bem-humorada ao “joelho cansado” do nosso colega Igor. O nome cola, quebra o gelo e deixa o aprendizado memorável.

---

## 🎯 Objetivos
- Aprender o **pipeline de compiladores** de ponta a ponta.
- Mapear uma linguagem customizada para **C** com exemplos práticos.
- Usar nomes em **PT-BR** para reforçar a didática (`sejoelho`, `enquantoDoi`, …).

---

## 📁 Estrutura (atual)
- **`voidknee_compilador.py`** → compilador (Tokens→Parser→AST→Semântica→C).
- **`voidknee.ipynb`** → notebook de apresentação com exemplos e células Markdown.
- **`ex*_*.c`** → arquivos C gerados pelos exemplos (opcional).
- **`ex*_*.exe`** (Windows) → executáveis gerados pelo GCC ao compilar os `.c`.

> Observação: no VS Code/Windows, compilar um `ex1_condicional.c` normalmente cria `ex1_condicional.exe`. Essa correspondência 1:1 é **intencional** para facilitar a demonstração.

---

## 🔑 Palavras-chave (VoidKnee → C)
**Tipos:** `inteirao → int`, `flutuante → float`, `dobradura → double`  
**Controle:** `sejoelho/outracoisa → if/else`, `enquantoDoi → while`, `praCada → for`  
**E/S:** `mostraAi(...) → printf(...)` (concatenação com `+`), `entradaAi(x) → scanf("%d|%f|%lf", &x)`  
**Booleanos:** `verdadeiro/falso → 1/0`  
**Comentário especial:** `/// texto` → `/* texto */` no C

---

## 🧠 Pipeline (resumo)
```
Fonte (.vk)
  → Léxico (Tokens)
  → Parser (AST)
  → Semântica (tabela de símbolos, checagens)
  → Gerador de Código (C)
  → Compilação (gcc) → Executável
```

---

## ▶️ Como rodar (CLI)
Pré-requisitos:
- **Python 3.10+**
- **GCC** (Windows: MinGW-w64/WinLibs/MSYS2; macOS: Xcode CLT; Linux: build-essential)

Verifique:
```bash
python --version
gcc --version
```

Gerar C:
```bash
python voidknee_compilador.py programa.vk -o programa.c
```

Gerar e executar:
```bash
python voidknee_compilador.py programa.vk --run
```

Sem arquivo `.vk`? Dá pra pipar:
```bash
echo "inteirao x; x = 3; mostraAi(\"x = \" + x + \"\\n\");" | python voidknee_compilador.py --run
```

---

## 💻 Rodando pelo VS Code

### Extensões recomendadas
- **Python** (ms-python.python)
- **Jupyter** (ms-toolsai.jupyter) — para o `.ipynb`
- **C/C++** (ms-vscode.cpptools) — para compilar/rodar C
- *(Opcional)* **Code Runner** (formosa-labs或Jun Han) — rodar trechos rápidos

### Passo a passo
1. Abra a pasta do projeto no VS Code.
2. Garanta que `gcc` esteja no `PATH` (no Windows, MinGW-w64 instalado).
3. Abra um `.c` gerado (ex.: `ex1_condicional.c`).
4. Pressione **Ctrl+Shift+B** e escolha **“C/C++: gcc.exe build active file”**.
   - Isso roda algo como:
     ```bash
     gcc "${file}" -o "${fileDirname}\${fileBasenameNoExtension}.exe"
     ```
   - Resultado: `ex1_condicional.c` → `ex1_condicional.exe`.
5. Rode o `.exe` pelo terminal integrado:
   ```bash
   .\ex1_condicional.exe
   ```

> **Dica:** Se preferir, crie/ajuste `.vscode/tasks.json` para garantir o nome do `.exe` igual ao do `.c`.

Exemplo de `tasks.json`:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "gcc.exe build active file",
      "type": "shell",
      "command": "gcc",
      "args": [
        "-g",
        "${file}",
        "-o",
        "${fileDirname}\\${fileBasenameNoExtension}.exe"
      ],
      "group": { "kind": "build", "isDefault": true },
      "problemMatcher": ["$gcc"]
    }
  ]
}
```

---

## 🧪 Exemplo rápido (VoidKnee → C)
VoidKnee:
```text
inteirao vida = 3;
sejoelho (vida > 0) {
    mostraAi("Vida: " + vida + "\n");
}
```

C gerado:
```c
#include <stdio.h>

int main(void) {
    int vida;
    vida = 3;
    if ((vida > 0)) {
        printf("Vida: %d\n", vida);
    }
    return 0;
}
```

---

## ❗ Limitações atuais (intencionais)
- Sem **funções** e **arrays** (foco didático em um único `main`).
- Strings **apenas** como **literais** para `mostraAi` (concatenação com `+`).
- Tabela de símbolos **global** (sem escopos por bloco).
- `mostraAi` **não** adiciona `\n` automático (insira `"\n"` quando precisar).

---

## 🚀 Próximos passos
- Funções com retorno/parâmetros; `return`.
- Arrays e leitura múltipla em `entradaAi`.
- Tipo booleano nativo (`bool`) e operadores compostos (`+=`, `++`, …).
- Escopos por bloco, diagnostics (`--emit-tokens/ast/c`).

---

## ❓FAQ rápido
- **Por que aparece `.exe` quando compilo no Windows?**  
  Porque o VS Code/GCC usa `-o ${fileBasenameNoExtension}.exe`. É nossa **escolha** para ter mapeamento direto `arquivo.c` ↔ `arquivo.exe`.

- **Posso ver os Tokens/AST?**  
  Podemos expor flags (`--emit-tokens`, `--emit-ast`) se quisermos incluir no notebook (fácil de adicionar).

---

**Feito com 🦵 + 💻 + ☕.**
