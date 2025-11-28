# VoidKnee 🦵 → C / Assembly (README • V3)

Projeto da disciplina **Compiladores**.  
A **VoidKnee** é uma linguagem de brinquedo que agora, na **V3**, traduz para **C** *e* para um **assembly de máquina de pilha didática**, passando por um pipeline completo:

**Léxico → Parser/AST → Semântica → Otimizador (O0/O1/O2) → Backend (C / ASM)**.

---

## 🚀 Novidades da V3 em relação à V2

A V2 já tinha:

- Tipos numéricos e booleano (`inteirao`, `flutuante`, `dobradura`, `dorzinha`, `dorzona`, `verdadeQueDoi`);
- Controle de fluxo estável (`sejoelho/outracoisa`, `enquantoDoi`, `praCada`);
- Vetores/matrizes e I/O (`mostraAi`, `entradaAi`);
- Geração de C com `setlocale` para facilitar acentuação.

A **V3** adiciona foco em **funções, tipos e backend alternativo**:

1. **Funções e recursão**
   - Declaração no estilo C:
     ```voidknee
     inteirao fatorial(inteirao n) {
         sejoelho (n <= 1) {
             retorna 1;
         } outracoisa {
             retorna n * fatorial(n - 1);
         }
     }
     ```
   - Ponto de entrada explícito: `inteirao principal()`, que vira um `int main(void)` no C gerado.

2. **Casting explícito**
   - Sintaxe estilo C:
     ```voidknee
     x = (inteirao) y;
     y = (flutuante) x;
     z = (dobradura) (x + 1);
     b = (verdadeQueDoi) x;
     ```
   - Usado para corrigir conversões de tipo de forma controlada, com mensagens que sugerem o casting quando necessário.

3. **Erros didáticos**
   - Todas as fases lançam `ErroCompilacaoVoidKnee` com:
     - etapa (`"léxico"`, `"sintático"`, `"semântico"`);
     - linha e coluna;
     - mensagem pensada para aluno, ex.:
       > "Não é possível atribuir valor do tipo DORZONA em variável do tipo INTEIRO. Dica: use um casting explícito, ex.: (inteirao) ..."

4. **Níveis de otimização: O0 / O1 / O2**
   - `O0`: sem otimização, apenas checagens.
   - `O1`: *constant folding* em expressões (ex.: `2 + 3 * 4`, `1 && 0`).
   - `O2`: herda O1 e aplica simplificações leves de controle de fluxo (ex.: `sejoelho (0) { ... }` é eliminado).

5. **Backend alternativo em assembly de pilha**
   - Geração de um assembly simples, com instruções como:
     `PUSH`, `LOAD`, `STORE`, `ADD`, `SUB`, `MUL`, `DIV`, `JZ`, `JMP`, `CALL`, `RET`.
   - Útil para mostrar o *meio do caminho* entre a AST e um código de baixo nível.

6. **VM em Python para o assembly**
   - Arquivo `vm_voidknee.py` interpreta o `.asm` gerado pela V3.
   - Permite executar o programa **sem depender de assembler real**, ideal para demonstração em aula.

---

## 🧱 Estrutura básica do projeto

(Exemplo de layout dentro de `voidknee/src`):

```text
src/
  compiler/
    voidknee_compiladorV1.py
    voidknee_compiladorV2.py
    voidknee_compiladorV3.py   # esta versão
  notebooks/
    voidkneeV1.ipynb
    voidkneeV2.ipynb
    voidkneeV3.ipynb           # apresentação da V3
  out/
    v3_A_fatorial_V3.c
    v3_E_fatorial_asm_V3.asm   # exemplos gerados
vm_voidknee.py                 # VM para o assembly da V3
READMEV1.md
READMEV2.md                    # README da V2
READMEV3.md                    # este arquivo
