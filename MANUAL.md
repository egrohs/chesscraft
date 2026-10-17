# ChessCraft - Manual de Regras

> Um roguelike tático para PC inspirado em *Hoplite*, com tema de fantasia sombria.
> Você é um mago atravessando um campo de batalha em grade para abrir uma linha
> de fogo contra o Rei inimigo. Cada turno é uma decisão de xadrez: leia as
> ameaças, posicione-se e encontre o ângulo para atacar.

Este manual descreve todas as regras do jogo. Para instalação e controles
rápidos, veja também o `README.md`.

---

## 1. Visão geral

- **Gênero:** roguelike tático por turnos, em grade.
- **Objetivo de cada fase:** matar o **Rei inimigo** no topo do campo.
- **Objetivo da run:** descer o máximo de andares possível antes de morrer.
- **Tema:** o mago (você) contra inimigos que se movem e atacam como peças de
  xadrez. Aprender feitiços exige resolver táticas de xadrez em santuários.

O jogo combina duas camadas:

1. **Combate tático** em grade (movimento, feitiços, linha de visão, IA de peças).
2. **Progressão roguelike** (fases geradas, dificuldade crescente, morte
   permanente da run, meta-progressão persistente de táticas dominadas).

---

## 2. O ciclo de jogo

1. **Atravesse o campo.** Por turno você faz **uma** ação (mover uma célula
   **ou** lançar um feitiço); depois **todos** os inimigos agem. Chegue a uma
   posição com linha limpa até o Rei inimigo.
2. **Mate o Rei.** O Rei fica murado no topo, guardado por inimigos. Crie uma
   abertura e acerte-o com um feitiço.
3. **Desça.** Quando o Rei cai, as peças somem e você pega as escadas para um
   andar mais profundo e difícil. Feitiços e vida são mantidos.
4. **Aprenda nos santuários.** Pise num santuário brilhante para escolher um de
   três feitiços novos e resolver um puzzle de xadrez temático para dominá-lo.
5. **A morte encerra a run** - mas táticas resolvidas de primeira são
   memorizadas para sempre e podem ser aprendidas sem o teste na próxima vez.

---

## 3. O campo de batalha

O campo é uma grade de células. As coordenadas crescem para a direita (x) e
para baixo (y). O mago começa embaixo; o Rei inimigo fica no topo.

### 3.1 Terreno

| Terreno        | Atravessável? | Bloqueia visão? | Observações |
| -------------- | :-----------: | :-------------: | ----------- |
| **Chão**       | Sim           | Não             | Célula livre comum. |
| **Parede**     | Não           | Sim             | Bloqueia movimento e linha de visão. |
| **Pilar**      | Não           | Sim             | Bloqueia movimento e linha de visão. |
| **Entulho**    | Não           | **Não**         | Bloqueia movimento, mas **não** bloqueia visão. |
| **Santuário**  | Sim           | Não             | Pisar nele abre a cena de aprendizado (1x por fase). |
| **Escadas**    | Sim           | Não             | Saída que aparece onde o Rei estava, após ele cair. |

> **Dica visual:** paredes, pilares e entulho são desenhados com relevo e
> contorno claro para você identificar de imediato o que **não** pode ser
> atravessado.

### 3.2 Linha de visão (LOS)

- A visão é traçada em linha reta (algoritmo de Bresenham) entre duas células.
- **Paredes e pilares** bloqueiam a visão. **Entulho não bloqueia.**
- Feitiços que exigem linha de visão falham se houver parede/pilar no caminho.

### 3.3 Movimento

- Você se move **ortogonalmente** (cima, baixo, esquerda, direita), **uma
  célula por ação**.
- Células alcançáveis são destacadas no seu turno.
- Você **não** pode entrar em células bloqueantes nem ocupadas por inimigos.

---

## 4. Turnos e ações

- **Uma ação por turno:** mover **ou** lançar um feitiço.
- Depois da sua ação, ocorre a **fase inimiga**: cada inimigo vivo age (ataca
  se puder, senão avança na sua direção).
- **Encerrar turno:** pressione `Espaço` ou o botão **End Turn** para passar
  sem agir (os inimigos ainda agem).
- **Contador de turnos** aparece no HUD.

### 4.1 Ordem de resolução

1. Você age (move ou conjura).
2. Verifica-se vitória imediata (Rei morto pelo feitiço).
3. Fase inimiga: cada inimigo ataca ou avança.
4. Cooldowns dos seus feitiços diminuem em 1.
5. Verifica-se o resultado: vitória (Rei morto), derrota (você com 0 de vida)
   ou jogo em andamento.

---

## 5. Você: o Mago

| Atributo        | Valor inicial | Regras |
| --------------- | :-----------: | ------ |
| **Vida (HP)**   | 6             | Chegar a 0 encerra a run (derrota). |
| **Escudo**      | 0             | Cada ponto absorve **um** golpe inimigo. |
| **Feitiços**    | Arcane Bolt, Blink | Os demais são aprendidos em santuários. |

- A vida e os feitiços **são mantidos** entre andares (ao descer).
- O escudo (Aegis) também é mantido entre andares.
- Cada golpe inimigo que acerta você tira **1 de vida** (ou consome 1 de
  escudo, se houver).

---

## 6. Inimigos (peças de xadrez)

Todos os inimigos têm padrões **previsíveis**, para que você leia o tabuleiro
como um puzzle. As células vermelhas mostram **onde eles podem atacar**.

| Inimigo   | Ameaça (ataque)                         | Movimento (aproximação)            | Vida |
| --------- | --------------------------------------- | ---------------------------------- | :--: |
| **Peão**  | As duas diagonais **à frente** (para baixo) | Só marcha para frente (nunca recua) | 2 |
| **Torre** | Linhas e colunas (até 8 células)        | Ortogonal na direção do mago       | 3 |
| **Bispo** | Diagonais (até 8 células)               | Diagonal na direção do mago        | 2 |
| **Cavalo**| Salto em "L" (8 casas)                  | Salta em "L" rumo ao mago          | 2 |
| **Rei**   | As 8 direções adjacentes                | As 8 direções rumo ao mago         | 3 |

Regras gerais da IA:

- Se o mago estiver **na área de ameaça** e houver linha de visão, o inimigo
  **ataca** (1 de dano).
- Caso contrário, ele **avança** respeitando seu padrão de movimento e, se
  puder atacar após mover, ataca.
- **Paredes e pilares** interrompem as linhas de ataque (Torre/Bispo). O
  **entulho** bloqueia o movimento, mas não a linha de ataque.
- O **Rei inimigo** é o alvo da fase: matá-lo vence o andar.

> **Leitura tática:** o mapa de ameaças (células vermelhas) é a sua principal
> ferramenta. Planeje o movimento para sair das linhas de ataque e, ao mesmo
> tempo, abrir uma linha limpa até o Rei.

---

## 7. Feitiços

Cada feitiço tem **alcance**, **cooldown** e regras próprias. Você começa com
**Arcane Bolt** e **Blink**; os demais são aprendidos em santuários.

| Feitiço          | Tipo        | Alcance | Dano | Cooldown | Regra |
| ---------------- | ----------- | :-----: | :--: | :------: | ----- |
| **Arcane Bolt**  | Projétil    | 6       | 2    | 0        | Voa em **linha reta** (linha/coluna/diagonal) e acerta o **primeiro** inimigo com linha de visão. |
| **Blink**        | Teleporte   | 5       | -    | 2        | Teleporta para qualquer célula **visível** e livre dentro do alcance. |
| **Arcane Blast** | Área        | 5       | 2    | 2        | Explosão de **raio 1** numa célula visível; atinge **todos** os inimigos na área. |
| **Aegis**        | Escudo      | -       | -    | 3        | Levanta uma proteção que **absorve o próximo golpe**. Dura até quebrar. |
| **Phase Lance**  | Projétil    | 7       | 2    | 2        | Como o Bolt, mas **ignora paredes e pilares** (não precisa de LOS). |
| **Ricochet**     | Projétil    | 7       | 2    | 2        | Voa e **ricocheteia uma vez** na primeira parede, seguindo a linha refletida. |
| **Dominate**     | Encantamento| 4       | -    | 4        | Converte um inimigo visível em **aliado por 3 turnos**; depois ele vira pó. Não funciona no Rei. |

#### Feitiços de tática de xadrez

Cada um destes feitiços é ensinado por uma **tática de xadrez** específica.

| Feitiço            | Tática (xadrez)      | Tipo        | Alcance | Dano | Cooldown | Regra |
| ------------------ | -------------------- | ----------- | :-----: | :--: | :------: | ----- |
| **Open Lines**     | Abrir linhas         | Empurrão    | 5       | -    | 2        | Empurra um inimigo (e os que estiverem atrás) **1 casa para longe** ao longo da linha, abrindo um corredor. Não afeta o Rei. |
| **Pawn Break**     | Pawn break           | Ruptura     | 4       | -    | 3        | **Destrói** uma parede, pilar ou entulho, abrindo um buraco na defesa. |
| **Windmill**       | Windmill             | Área (cruz) | 8       | 2    | 4        | Golpeia **todos** os inimigos na sua **linha e coluna** (a cruz do seu rank/file). |
| **Fork**           | Garfo / Duplo        | Multi-alvo  | 5       | 2    | 2        | Atinge **dois** inimigos: o alvo e o inimigo mais próximo ao lado dele. |
| **Sacrifice**      | Sacrifício           | Utilidade   | -       | -    | 3        | Paga **1 de vida** para ganhar **2 de escudo** e **zerar todos os cooldowns**. |
| **Stalemate**      | Afogado              | Fuga        | 6       | -    | 3        | Teleporta para a célula **mais segura** visível (a mais longe das ameaças). |
| **Deflection**     | Desvio               | Medo        | 4 (raio 2) | - | 3        | Inimigos próximos **fogem 1 casa** de você neste turno e **não atacam**. |
| **Discovered Attack** | Ataque descoberto | Tempo       | 6       | 2    | 3        | Causa dano **e concede uma ação extra** neste turno (ganha tempo). |
| **Pin**            | Cravada (pin)        | Controle    | 5       | -    | 3        | **Imobiliza** um inimigo por **2 turnos**: ele não move nem ataca. Não afeta o Rei. |
| **Minefield**      | Trap                 | Armadilha   | 5       | 3    | 2        | Coloca uma **mina** numa célula de chão; ela só detona quando um **inimigo** pisa nela. |
| **Triangulation**  | Triangulação         | Tempo       | -       | -    | 2        | Perde um tempo: ganha **1 de escudo** e **reduz todos os cooldowns em 1**. |
| **Skewer**         | Espeto (skewer)      | Sniper      | 7       | 2    | 2        | Tiro perfurante que **ignora o primeiro** inimigo da linha e acerta o **de trás**. |
| **Interference**   | Interference         | Muro        | 5       | -    | 3        | Ergue um **muro temporário** (3 turnos) que **corta linha de visão** e tiros. |
| **Clearance**      | Clearance            | Reposicion. | 1       | -    | 2        | Dá um passo lateral para uma casa adjacente, **empurrando** o inimigo ali 1 casa adiante. |

### 7.1 Detalhes importantes

- **Linha reta:** Bolt e Phase Lance só podem ser lançados em linha/coluna/
  diagonal em relação ao mago.
- **Cooldown:** após conjurar, o feitiço fica indisponível por N turnos (o
  contador diminui ao fim de cada turno).
- **Cargas:** alguns feitiços podem ter cargas limitadas (quando aplicável).
- **Dominate:** o inimigo dominado ataca o **inimigo hostil mais próximo** e
  **desaparece** ao fim dos 3 turnos.
- **Aegis:** cada conjuração adiciona 1 ponto de escudo; cada golpe consome 1.

---

## 8. Santuários e puzzles de xadrez

Santuários são a forma de **aprender feitiços**.

### 8.1 Fluxo do santuário

1. **Pise** numa célula de santuário (só funciona **uma vez por fase**).
2. Escolha **um de três** feitiços oferecidos (que você ainda não conhece).
3. Resolva o **puzzle de xadrez temático** daquele feitiço.
4. Ao resolver, você **aprende** o feitiço.

> O santuário só pode ser visitado **uma vez por fase**. Depois de usado, ele
> fica acinzentado e age como chão comum.

### 8.2 Regras do puzzle

- Você joga o lado que **tem o turno** na posição inicial.
- As respostas do oponente são **roteirizadas** - é um desafio de "encontrar a
  linha", determinístico.
- **Jogada certa:** avança na solução.
- **Jogada errada:** o puzzle **reinicia** e você **perde 1 de vida** (mínimo 1).

### 8.3 Domínio permanente (meta-progressão)

- Se você resolver o puzzle **de primeira** (sem errar), a tática é gravada
  **permanentemente** no seu perfil.
- Em runs futuras, feitiços cuja tática você já domina podem ser aprendidos
  **sem o teste**.

### 8.4 Feitiço x tema tático

| Feitiço        | Tema tático          | Puzzle          |
| -------------- | -------------------- | --------------- |
| Arcane Bolt    | A coluna aberta      | `t_line`        |
| Blink          | O passo silencioso   | `t_reposition`  |
| Arcane Blast   | A grande diagonal    | `t_area`        |
| Aegis          | A fortaleza          | `t_defence`     |
| Phase Lance    | O cavalo saltador    | `t_pierce`      |
| Ricochet       | A linha descoberta   | `t_reflect`     |
| Dominate       | O cravamento (pin)   | `t_charm`       |
| Open Lines     | Abrir linhas         | `t_open_lines`  |
| Pawn Break     | Pawn break           | `t_pawn_break`  |
| Windmill       | Windmill             | `t_windmill`    |
| Fork           | Garfo / Duplo        | `t_fork`        |
| Sacrifice      | Sacrifício           | `t_sacrifice`   |
| Stalemate      | Afogado              | `t_escape`      |
| Deflection     | Desvio               | `t_deflection`  |
| Discovered Attack | Ataque descoberto | `t_discovered`  |
| Pin            | Cravada              | `t_pin`         |
| Minefield      | Trap                 | `t_trap`        |
| Triangulation  | Triangulação         | `t_tempo`       |
| Skewer         | Espeto               | `t_skewer`      |
| Interference   | Interference         | `t_interference`|
| Clearance      | Clearance            | `t_clearance`   |

---

## 9. Progressão roguelike

### 9.1 Andares (profundidade)

- Cada run começa no **andar 1**.
- Ao matar o Rei, você **desce** para o próximo andar, mais difícil.
- O tabuleiro **cresce** levemente com a profundidade (até um limite).
- O **orçamento de inimigos** cresce com a profundidade:

| Inimigo | Quantidade no andar `d` |
| ------- | ----------------------- |
| Peão    | `2 + d`                 |
| Torre   | `1 + d // 2`            |
| Bispo   | `1 + (d + 1) // 2`      |
| Cavalo  | `d // 2`                |

- O Rei inimigo tem **3 de vida** e fica murado num "castelo" no topo, com um
  único portão.

### 9.2 Morte e persistência

- **Vida a 0 = derrota.** A run termina.
- **Meta-progressão persistente:** táticas resolvidas de primeira ficam salvas
  no perfil (`saves/profile.json`) e valem para todas as runs futuras.
- O perfil também guarda o **melhor andar alcançado** e o **número de runs**.

### 9.3 Herói (perfil)

O perfil guarda estatísticas do herói que evoluem com o tempo:

- **Nível, XP, ouro, rating.**
- **Atributos:** Táticas, Foco, Resolução (crescem ao subir de nível).
- **Táticas dominadas** (feitiços aprendidos de primeira).
- **Melhor profundidade** e **runs** jogadas.

---

## 10. Vitória e derrota

| Resultado   | Condição |
| ----------- | -------- |
| **Vitória da fase** | O Rei inimigo é morto. Você desce para o próximo andar. |
| **Derrota** | Sua vida chega a 0. A run termina. |

Não há "fim" fixo: o objetivo é descer o máximo possível. A morte é esperada -
o que permanece é a **meta-progressão** das táticas dominadas.

---

## 11. Controles

| Ação                  | Entrada |
| --------------------- | ------- |
| Mover                 | Clique numa célula alcançável destacada |
| Selecionar feitiço    | Clique no card ou tecla `1`-`9` |
| Lançar feitiço        | Com feitiço pronto, clique num alvo destacado |
| Encerrar turno        | `Espaço` ou botão **End Turn** |
| Voltar ao modo mover  | `Tab` ou clique direito |
| Abandonar run         | `Esc` ou botão de voltar |

---

## 12. Dicas de sobrevivência

- **Leia o vermelho.** As células de ameaça são a informação mais importante.
- **Use o entulho a seu favor:** ele bloqueia o movimento inimigo, mas não a
  sua visão - você pode atirar por cima dele.
- **Quebre a linha de visão** com paredes/pilares para escapar de Torres e
  Bispos.
- **Blink** é ótimo para reposicionar sem atravessar o espaço entre as células
  (e para fugir de uma armadilha).
- **Aegis antes de avançar** em terreno aberto pode salvar sua vida.
- **Dominate** transforma um inimigo perigoso em aliado temporário - ótimo para
  abrir caminho até o Rei.
- **Phase Lance** e **Ricochet** resolvem situações em que o Bolt não tem linha
  limpa.
- **Resolva puzzles de primeira** para dominar táticas permanentemente e
  facilitar runs futuras.

---

## 13. Glossário

- **Run:** uma tentativa completa, do andar 1 até a morte.
- **Andar / profundidade:** uma fase gerada; descer = andar mais difícil.
- **LOS (linha de visão):** caminho reto entre duas células, bloqueado por
  paredes/pilares.
- **Ameaça:** célula que um inimigo pode atacar a partir da posição atual.
- **Cooldown:** turnos de espera antes de reusar um feitiço.
- **Santuário:** célula que abre o aprendizado de feitiços (1x por fase).
- **Tática dominada:** puzzle resolvido de primeira, salvo permanentemente.
- **Meta-progressão:** o que persiste entre runs (táticas dominadas, recordes).
