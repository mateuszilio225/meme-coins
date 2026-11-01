# Contabilidade e viabilidade com R$400 fictícios

## O que é observado versus assumido

Preço/volume/liquidez são campos do provedor, quando presentes. Nenhum deles é um fill confirmado. Todas as taxas USD, impacto linear, slippage, spread, latência e capacidade dos cenários são **hipóteses de pesquisa não calibradas**. Não representam orçamento garantido nem recomendação de tamanho. O programa não converte capital fictício em dinheiro real.

Uma carteira começa com `400 / FX_inicial` USD contábeis. Carteiras independentes são experimentos contrafactuais. Os três cenários de `main` são trajetórias alternativas de um único capital inicial, nunca três contas que se somam. O FX não é reprecificado para esconder perdas; BRL usa equivalência inicial, e não uma alegação de câmbio atual.

## Ponto de equilíbrio implementado

Para orçamento total B, preço de referência P, liquidez efetiva L, fee f, meia amplitude de spread + slippage h, rede/prioridade N e k = 2 × multiplicador_de_impacto / L:

- Fill de compra: `P × (1 + h + kB)`.
- Quantidade: `q = (B − N) / [(1 + f) × P × (1 + h + kB)]`.
- Venda: notional de referência `x = q × P × (1 + retorno)`.
- Caixa de venda: `x × (1 − h − kx) × (1 − f) − N`.
- Igualar o caixa de venda a B fornece a primeira raiz de equilíbrio. Discriminante negativo significa que o modelo não encontra equilíbrio nessa curva. Raiz não prova viabilidade de rota/capacidade.

Impacto na compra usa o orçamento total como referência conservadora explicitamente definida. Na saída usa o notional da quantidade efetiva, dependente do preço de saída. O custo embutido no preço só é registrado para decomposição, sem segundo débito de caixa. Fees e rede são explícitos. Parcial/trailing criam mais fills e mais custos; a tabela simples de ida e volta não os esconde como gratuitos.

### Exemplo exclusivamente ilustrativo

FX fictício **5 BRL/USD**, liquidez reportada US$10.000, parâmetros distribuídos, uma compra + venda integral. Estes números são cálculo do modelo, não dados de mercado:

| Posição BRL | Optimistic | Base | Adverse |
|---:|---:|---:|---:|
| 10 | 2,717% | 5,002% | 16,111% |
| 20 | 2,287% | 4,041% | 13,049% |
| 30 | 2,198% | 3,779% | 12,293% |
| 40 | 2,196% | 3,690% | 12,102% |
| 80 | 2,397% | 3,765% | 12,752% |

O comando `economics` recalcula com o FX do protocolo e disponibiliza outras liquidez/tamanhos. A tabela não libera posições de R$80: a política inicial limita cada entrada a **R$40 equivalentes**, exposição a R$120 e três posições/ordens. O tamanho maior pode elevar impacto, e o menor aumenta o peso de custos fixos.

O gate de custo inicial é equilíbrio máximo de 8%. Sob essas hipóteses, o adverso acima é recusado. Não sabemos se o ativo teria retorno esperado superior ao equilíbrio, mesmo nos casos aceitos. Gate de custo não é previsão de retorno.

## Custos recorrentes

`(infra_mensal_brl + dados_mensal_brl) × segundos_decorridos / (30 × 86400)` é contabilizado **uma vez no resultado global de cada carteira hipotética**, sem desconto adicional em cada fill. Cada carteira reportada é uma alternativa completa de operação. Não somar custos/lucros entre carteiras para alegar um portfólio único. Caixa parado sem sistema é baseline de R$400 sem taxa de infraestrutura.

R$20/mês consomem 5% do capital por mês; R$50, 12,5%; R$100, 25%, antes de trading. O custo zero padrão não foi confirmado e impede conclusão de vantagem econômica. Não há contratação de dados. Maior frequência multiplica custos variáveis e pode piorar o resultado.

## Abstenção pré-registrada

Abster-se se não houver histórico mínimo, par/fonte consistentes, frescor local, liquidez/capacidade, limites de caixa/exposição, orçamento para rede ou se o equilíbrio exceder 8%. C acrescenta riscos observados e desconhecidos definidos. `main` e `main_random` exigem ida e volta indicativa com quantidade atômica e orçamento correspondentes, recente até 30 s. Uma quote não verifica a venda posterior e não converte o fill em execução real. Sem chave/rota: abstenção, sem taxa de rede inventada.

Os filtros também recusam vencedoras. As recusas ficam em `decisions` e eventos `abstain`; a análise `missed` acompanha altas posteriores sem transformar o passado em compra válida. A correlação não isola causalidade de seleção/atraso. `ablate` isola duas mudanças de execução sobre sinais fixos, mantendo as demais condições.

## Resultado completo

Mostram-se ordens expiradas/frustradas, caixa, reservas, PnL fechado, parcial realizada, posições abertas/inconclusivas, patrimônio marcado antes dos custos de saída, idade desse patrimônio e estresse de recuperação zero. Se não há preço fresco, a marcação fica indisponível. O estresse de recuperação zero **não é baixa realizada** e não libera capital.

A expectativa fica indefinida enquanto há posições ou ordens pendentes; quando definida, usa todas as ordens registradas, incluindo frustradas/expiradas. A taxa de acerto e o profit factor de encerradas são rotulados como condicionais e nunca substituem o resultado global. Sem limite superior defensável de recuperação, não inventamos bound superior nem probabilidades. Para os cenários de perda total, o caixa remanescente fornece o estresse inferior, não uma previsão.

Atribuição contábil é possível para fees/rede/custos de preço. Separar causalmente seleção, atraso de descoberta, entrada e regra de saída requer dados/contrafactuais adequados: o forensics deixa essa causa como `unknown` em vez de atribuir toda perda ao filtro.

## Conclusão desta entrega

- Vantagem identificável: **nenhuma demonstrada em dados reais futuros**.
- Quanto os custos consomem: calculável condicionalmente por orçamento e cenário; percentual empírico de lucro consumido é desconhecido.
- Dependências não verificadas: execução, calibração de custos, cobertura de fontes, disponibilidade de venda e desempenho futuro.
- Próximo experimento de maior valor: validar coleta e quotes no tamanho efetivo, medir bloqueios/saídas e congelar acompanhamento futuro. Sem isso, não operar é a decisão justificável.
