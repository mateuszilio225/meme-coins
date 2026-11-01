# Protocolo de pesquisa v0.1.0

Cada banco tem um protocolo único, congelado no `init`, com SHA-256 do JSON canônico de **toda** a configuração. Registro inclui capital, FX disponível, features, políticas de seleção/execução, cenários, seed e calendário. Configuração divergente impede `run`; nova hipótese exige banco e registro novos. Não reinicializar o antigo. O prompt recebido está preservado como especificação, não como alegação de funcionalidades antigas.

## Calendário

A partir do instante UTC do registro: desenvolvimento 7 dias; embargo 1 dia; validação 20 dias; embargo 1 dia; teste 20 dias. Um mint pertence ao período da primeira observação; não vira nova amostra em outro período nem usa outra pool como atalho. Mints vistos primeiro no embargo não entram na rodada. Feature usa só observações do mesmo mint/par/fonte disponíveis e consumidas até o timestamp de referência. Resultados não atravessam o fim do período. Posições sem saída no encerramento são inconclusivas, sem liberar capital.

Validação/teste ficam ocultos nos relatórios até o fim correspondente. Avaliação final exige período encerrado. SQLite e código local não são barreira contra um administrador que deliberadamente remova os controles. Não existe promoção automática nem modo de operar dinheiro real.

## Hipóteses e seleção congeladas

A — Early Momentum: retorno entre 2% e 35% (20 pontos), velocidade positiva (15), aceleração positiva (15), compras ≥60% (15), drawdown local ≤5% (10), volume m5 ≥US$1.000 (10), razão de volume nominalmente não sobreposto ≥1,2 (15).

B — Continuation: cinco observações, passos positivos ≥75% (20), nova máxima (15), compras ≥60% (10), mudança da fração compradora ≥−5pp (10), velocidade positiva (10), razão nominalmente não sobreposta ≥0,8 (20), aceleração ≥−0,02/min² (15).

C — Mesmo potencial de A, rejeitando retenção de liquidez <80%, compras <50%, drawdown ≥15%, volatilidade >0,25/minuto, alta local >100%, campos de risco citados ausentes e riscos conhecidos de autoridade/programa. Segurança não verificada continua explicitamente desconhecida. C não certifica tokens.

Limiar 60; histórico 900 s; pelo menos três observações com espaçamento 30 s; gaps até 180 s; preço/liquidez mínimos e idade do par até 120 min. Veja o TOML para os parâmetros completos. Meia amplitude de spread entra em cada lado. Velocidade = retorno fracionário / minutos do intervalo; aceleração compara velocidades pela distância entre centros; volatilidade = desvio-padrão populacional dos log-retornos por minuto. A razão m5 usa observações separadas por 300–480 s, sem alegar reconstruir transações independentes.

Em cada ciclo, um par representativo por mint com maior liquidez reportada; em seguida top 1 contemporâneo por modelo, desempate SHA-256 com seed 3501. Decisões e ranks de todos os candidatos são persistidos. Campos ausentes não ganham pontos. Observações antigas não são reapresentadas como novos alertas após restart.

Baselines: aleatório por hash/seed, volume, momentum, fração compradora, primeiro elegível e controle por faixa de idade (±15 min) e log-liquidez (±0,7), sem reutilizar mint nesse modelo. `first` seleciona o primeiro disponível entre elegíveis no ciclo; não é estimativa de detecção completa de mercado.

`main` escolhe C se disponível e senão A, **definido antes dos resultados**; `main_random` recebe o aleatório, com gates de execução equivalentes. Todos os slots de `main` compartilham caixa e deduplicam mint. Baseline caixa mantém R$400, sem carregar custos da pesquisa. Não somar saldos de carteiras independentes.

## Finanças

Cada entrada reserva 10% do capital inicial; exposição máxima 30%, três slots, reserva mínima 10%, notional mínimo US$1, capacidade por fill até 0,5% da liquidez efetiva. Ordem expira em 180 s. Entrada/saída exigem requisição posterior ao gatilho + latência. TP 2x vende 50%, stop 40%, trailing 25% após parcial, duração máxima 60 min, saída por retenção de liquidez até 25%. Timeout de venda 600 s mantém posição inconclusiva. Stop não garante preço.

Variants de entrada suportadas: immediate, confirmation, consolidation, recovery. Variants de saída: fixed, volatility, momentum. A configuração inicial usa immediate/fixed. Não executar todas as combinações: a ablação predefinida contém referência + uma alteração de entrada + uma alteração de saída, exclusivamente em desenvolvimento e em bancos separados. Pesos não são treinados. `moonshot-scores` fornece remoção descritiva de componentes, sem alegação causal.

## Inferência, comparações e parada

Métrica primária: resultado líquido do portfólio em BRL equivalente ao FX inicial, incluindo custo recorrente global. Família primária fixa: A/B/C versus aleatório em três cenários, **nove comparações**. Baselines adicionais e `main` são descritivos/secundários, não uma busca por vencedor. Registro preserva todas as avaliações e tentativas no banco/saídas de ablação.

Gates preliminares: pelo menos 100 mints distintos encerrados por carteira, 20 dias observados, cobertura temporal ≥80%, nenhum unresolved/pendente, custos recorrentes confirmados e custos/fills externamente validados. A cobertura implementada soma intervalos entre ciclos com teto de 180 s e divide pelo período: mede continuidade global, não cobertura completa por token.

Incerteza: diferenças diárias pareadas, bootstrap circular com blocos de três dias, 30.000 reamostragens, alpha 0,05/9. Recusar estimar cauda se menos de 50 draws esperados em cada cauda. Sensibilidade com blocos de um e sete dias. Isso é descritivo e depende de estacionariedade/representatividade não comprovadas; mais reamostragens não fabricam mais dias independentes. Carteiras/cenários não multiplicam o número de tokens independentes.

Avaliar ao fim fixo da validação e ao fim fixo do teste, sem parada antecipada por lucro e sem olhar repetidamente para ajustar. Desenvolvimento não é confirmação. Repetir o comando é registrado, mas não cria evidência nova. A implementação nunca promove automaticamente e mantém `insufficient_evidence` enquanto a execução permanecer não verificada.

Robustez entregue: cenários com trajetórias próprias, retirada do maior e dos três maiores PnLs encerrados, drawdown observado com gaps explícitos e estresse de recuperação zero; bootstrap diário pareado e sensibilidade de blocos. Leave-group-out de token/dia/hora/faixa de liquidez é descritivo sobre operações encerradas; análises causais completas por regime e benchmark líquido SOL ainda não foram implementadas.
