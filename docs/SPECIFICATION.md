# MOONSHOT PROFIT RESEARCH — CRIAR DO ZERO UM SISTEMA COMPLETO DE PESQUISA DE MEME COINS NA SOLANA

## 1. Missão principal

Desenvolva do zero um projeto completo, funcional e documentado para descobrir, acompanhar e analisar meme coins na Solana, emitir alertas prospectivos e testar estratégias de compra e venda com dinheiro fictício.

O componente central deve ser um **Moonshot Radar**, voltado a identificar candidatas antes de grandes valorizações, investigar continuidade dos movimentos e evitar parte das reversões, perdas extremas e situações sem saída.

Meu objetivo econômico é pesquisar uma estratégia que consiga produzir lucro líquido fictício de maneira consistente depois de considerar custos, latência, liquidez, risco e limitações de execução.

Quero que você pesquise, formule hipóteses, implemente, teste, compare e rejeite abordagens ruins. Priorize o que pode melhorar o resultado econômico demonstravelmente.

**Este é um projeto novo. Não dependa de arquivos, ZIPs, código ou bancos de versões anteriores. Toda a especificação necessária está neste prompt.**

Execute o trabalho de engenharia. Não entregue apenas um plano, pseudocódigo, uma interface com dados inventados ou uma lista de recomendações.

O escopo desta implementação é pesquisa e simulação:

- Não conectar carteiras financiadas.
- Não solicitar chave privada ou seed.
- Não assinar ou transmitir transações.
- Não executar negociações reais.
- Não fabricar lucro ou afirmar vantagem sem evidência.
- Chaves opcionais de APIs de dados devem ficar em variáveis de ambiente e nunca aparecer nos logs.

## 2. Contexto das ideias anteriores

Um projeto anterior explorou esta evolução:

1. Monitoramento de tokens Solana com Python, APIs públicas e SQLite.
2. Três carteiras fictícias independentes A/B/C, com R$400 cada.
3. Registro de experiências de moedas aprovadas e rejeitadas.
4. Diagnóstico de filtros, oportunidades perdidas, cobertura e falhas de API.
5. Laboratório E0–E4 para comparar hipóteses de seleção.
6. Moonshot Radar MR1, com pontuação explicável e execução fictícia R0.
7. Moonshot Radar MR2, com modelos de momentum inicial, continuidade e seleção ajustada a risco, alimentando carteiras R1.
8. Diagnóstico de perdas, variantes de entrada/saída, baselines e investigação de quotes.

Use essa experiência como contexto conceitual. Você deve construir uma implementação nova e coerente, sem presumir que qualquer um desses módulos já existe.

Problemas observados anteriormente:

- Filtros conservadores frequentemente impediam todas as operações por falta de dados verificáveis.
- Muitas chamadas RPC recebiam HTTP 429.
- Algumas moedas subiam muito, mas o radar não as selecionava antes.
- Scores altos não demonstraram boa relação com lucro.
- Entradas aparentemente promissoras terminaram em perdas.
- Uma operação positiva no cenário base podia ficar negativa no adverso.
- Liquidez e timestamps de preço frequentemente estavam ausentes.
- Existia dificuldade para distinguir alta observada de oportunidade realmente negociável.

Uma pequena amostra relatada pelo usuário teve 67 tokens, dez alertas e seis operações encerradas no cenário base: um ganho e cinco perdas, com resultado aproximado de −US$16,11.

Também houve relato de três moedas que atingiram +100% em uma janela de 30 minutos sem terem sido selecionadas pelo radar.

Esses relatos não vêm acompanhados do banco original. Não tente reconstruir mints, preços ou causas específicas. Eles servem para orientar perguntas de pesquisa, não como dataset de treinamento ou evidência estatística.

## 3. O que significa sucesso

Separe dois objetivos.

### Sucesso técnico

O programa:

- Instala e executa corretamente.
- Coleta dados reais quando as fontes estão disponíveis.
- Preserva histórico.
- Explica decisões.
- Emite alertas somente com informações disponíveis naquele momento.
- Simula operações e custos corretamente.
- Mostra perdas, falhas e posições inconclusivas.
- Funciona no Windows com comandos simples.

### Sucesso econômico de pesquisa

Uma estratégia apresenta evidência futura de vantagem líquida em relação a baselines, respeitando o mesmo capital, custos, calendário e restrições.

A métrica principal deve ser o resultado líquido do portfólio, acompanhado de drawdown, exposição, incerteza e capacidade de saída.

Não considere sucesso econômico apenas:

- Encontrar uma moeda que posteriormente subiu.
- Emitir muitos alertas.
- Ganhar em uma demonstração sintética.
- Ter alta taxa de acerto com perdas ocasionais enormes.
- Selecionar retrospectivamente a melhor estratégia.
- Mostrar lucro antes dos custos.
- Excluir operações sem saída.

Se a pesquisa não encontrar vantagem, entregue essa conclusão e os dados que a sustentam.

## 4. Pesquisa técnica e quantitativa antes das decisões

Pesquise documentação oficial vigente e estudos relevantes antes de implementar integrações ou escolher métodos.

Investigue:

- Descoberta de novos tokens e pools.
- Cobertura e viés dos feeds disponíveis.
- Dados de preço, volume, compras, vendas e liquidez.
- Segurança e particularidades de tokens Solana.
- Quotes indicativas de compra e venda.
- Custos, slippage, impacto e latência.
- Estratégias de momentum, continuidade, reversão e abstenção.
- Validação temporal, sobreajuste e múltiplas comparações.

Para cada hipótese importante, registre:

1. Qual problema pretende resolver.
2. Qual evidência motivou a hipótese.
3. Por que poderia existir uma vantagem econômica.
4. Quais dados são necessários.
5. Quando esses dados ficam disponíveis.
6. Como será comparada a um baseline.
7. O que faria a hipótese ser rejeitada.

Use documentação primária para decisões de API. Tutoriais, redes sociais e prints de ganhos podem sugerir perguntas, mas não comprovam rentabilidade.

Não procure indefinidamente. Faça uma pesquisa inicial suficiente, implemente uma base funcional e aprofunde os pontos que os dados indicarem como gargalos.

## 5. Arquitetura do projeto

Use Python e SQLite, com arquitetura modular e dependências mínimas justificadas.

O projeto deve ter, no mínimo:

- Configuração validada.
- Clientes de dados.
- Controle de chamadas, cache e recuperação de falhas.
- Normalização e proveniência.
- Descoberta e acompanhamento de tokens/pares.
- Histórico persistente.
- Cálculo de indicadores.
- Moonshot Radar.
- Motor de decisões e registro de sinais.
- Simulador financeiro.
- Carteiras experimentais.
- Portfólio único.
- Diagnóstico de perdas.
- Oportunidades perdidas.
- Comparação de estratégias.
- Avaliação estatística.
- Relatórios e CLI.
- Testes automatizados.
- Demonstração offline separada.
- Documentação Windows.

O pacote Python pode se chamar `meme_research`.

Use um único coletor para alimentar os modelos com os mesmos dados disponíveis. Evite repetir consultas para cada indicador ou estratégia.

Separe claramente:

- Observações de mercado.
- Features calculadas.
- Decisões.
- Alertas.
- Ordens fictícias.
- Fills condicionais.
- Movimentações de caixa.
- Resultados observacionais.
- Avaliações de experimentos.

## 6. Fontes e controle de APIs

Investigue fontes oficiais/documentadas, incluindo quando adequadas:

- DEX Screener.
- Solana RPC somente leitura.
- Jupiter ou outro provedor autorizado de quotes.
- BCB PTAX para referência cambial.
- Provedores adicionais, caso tragam melhoria mensurável e tenham acesso permitido.

Não presuma que endpoints, planos ou limites continuam iguais aos de tutoriais antigos.

Implemente:

- Orçamento de chamadas por provedor.
- Limite de concorrência.
- Timeout.
- Validação de tamanho e conteúdo da resposta.
- Backoff com jitter.
- Respeito a Retry-After.
- Circuit breaker.
- Cache de sucessos e falhas.
- Persistência dos cooldowns.
- Deduplicação.
- Fila com prioridades.
- Registro de chamadas realmente feitas e consultas adiadas.

Não contorne bloqueios, quotas ou restrições com rotação de IP, contas ou endpoints.

APIs pagas devem ser opcionais, com custo e benefício explicados. Não contratar serviços automaticamente.

## 7. Identidade, tempo e qualidade dos dados

Cada registro deve identificar, quando disponível:

- Mint.
- Par/pool.
- Programa/DEX.
- Fonte.
- Timestamp da requisição.
- Timestamp do recebimento.
- Timestamp do provedor, se efetivamente fornecido.
- Preço e moeda de referência.
- Liquidez.
- Volume e janela correspondente.
- Compras/vendas e janela correspondente.
- Idade do par.
- Estado de qualidade.
- Payload original ou referência auditável.

Regras:

- Símbolo não é identificador único.
- Idade do par não é necessariamente idade do token.
- Ausente não é zero.
- Timestamp local não prova frescor do preço do provedor.
- Liquidez não pode ser inventada a partir de volume, FDV ou market cap.
- Supply total não comprova circulating supply.
- Top contas não equivalem automaticamente a top holders econômicos.
- Não misturar preços de pools diferentes para fabricar retorno.
- Metadados recebidos depois não podem aprovar decisões anteriores.
- Desaparecimento de dados não comprova, sozinho, fraude ou perda total.

Registre gaps, inconsistências, fingerprints repetidos, dados antigos e cobertura incompleta.

## 8. Moonshot Radar obrigatório

Crie um **Moonshot Radar explicável**, capaz de acompanhar o universo descoberto, registrar candidatos e emitir alertas prospectivos.

Pesquise três modelos principais.

### Modelo A — Early Momentum

Objetivo: detectar aceleração inicial antes de movimentos extremos.

Investigue:

- Retorno recente.
- Velocidade e aceleração do preço.
- Crescimento de atividade.
- Participação compradora.
- Liquidez.
- Idade do par.
- Consistência entre snapshots.
- Movimento relativo à volatilidade.
- Quanto da alta já ocorreu antes do sinal.

### Modelo B — Momentum Continuation

Objetivo: investigar quais movimentos têm maior possibilidade de continuar.

Investigue:

- Persistência do crescimento.
- Frequência de passos positivos.
- Novas máximas observadas.
- Manutenção de atividade.
- Mudança da pressão compradora.
- Reversões intermediárias.
- Desaceleração.
- Deterioração da liquidez.

### Modelo C — Risk-Adjusted Selection

Objetivo: evitar parte das perdas severas e condições economicamente ruins.

Investigue:

- Queda de liquidez.
- Pressão vendedora.
- Volatilidade excessiva.
- Movimento aparentemente exaurido.
- Falhas de atualização.
- Riscos conhecidos do token.
- Ausência de rota de saída.
- Impacto e custos altos para a posição.
- Incerteza dos dados.

Não presuma que cada filtro melhora o resultado. Meça também as oportunidades vencedoras que ele elimina.

Os modelos devem ter versões, regras e resultados separados.

## 9. Pontuação e interpretação

Separe, quando fizer sentido:

- **Moonshot Potential Score:** força dos sinais experimentais de movimento.
- **Execution Quality:** qualidade dos dados necessários para estimar entrada/saída.
- **Risk Assessment:** riscos identificados e informações desconhecidas.

Score 90/100 não deve ser exibido como 90% de chance de lucro.

Comece com regras explicáveis e poucas hipóteses. Não invente pesos “ótimos”.

Implemente:

- Resultado por faixa de score.
- Relação entre score e retorno posterior.
- Relação entre score e perdas extremas.
- Relação entre score e PnL líquido.
- Ablação de indicadores.
- Comparação com scores simples.
- Calibração fora da amostra, somente se houver dados suficientes.

Se houver ML, use validação temporal, controle de vazamento e orçamento limitado de experimentos. Todas as transformações e escolhas devem ser ajustadas apenas nos dados permitidos.

Não use split aleatório de snapshots do mesmo token.

## 10. Volume, fluxo e descoberta antecipada

Não trate duas janelas móveis m5 consecutivas como transações novas independentes.

Documente a semântica de cada indicador. Quando apropriado, compare janelas nominalmente não sobrepostas ou use eventos individuais de uma fonte autorizada.

Não reconstrua um fluxo exato de transações a partir de agregados incompletos.

Meça separadamente:

- Descoberta até primeira observação.
- Primeira observação até features prontas.
- Features prontas até alerta.
- Alerta até elegibilidade de entrada.
- Elegibilidade até primeira cotação utilizável.
- Gatilho de saída até cotação de venda.

Pesquise se fontes de eventos ou WebSocket melhoram a descoberta. Só implemente com decoder validado, deduplicação, reconexão, recuperação de lacunas e orçamento controlado.

Não prometa detecção em segundos sem demonstrar.

## 11. Seleção contemporânea e orçamento

Compare candidatos concorrentes com as informações efetivamente disponíveis no mesmo ciclo.

Evite selecionar apenas os primeiros tokens que chegaram.

Registre:

- Candidatos elegíveis.
- Rejeitados e seus motivos.
- Posição no ranking.
- Orçamento disponível.
- Sinais recusados por limite.
- Oportunidades recusadas por capital ou exposição.

Separe o limite de mensagens visuais do registro científico. O sistema pode limitar o que aparece na tela sem apagar candidatos e decisões.

Não reclassifique uma oportunidade como alerta emitido após descobrir que ela subiu.

## 12. Baselines e laboratório experimental

Crie referências simples para verificar se os modelos sofisticados acrescentam valor:

- Não operar.
- Seleção aleatória reproduzível.
- Maior volume.
- Maior momentum.
- Maior participação compradora.
- Primeiro instante elegível.
- Controle pareado por idade/liquidez quando viável.

Também permita hipóteses experimentais limitadas:

- Momentum com volume.
- Crescimento de atividade compradora.
- Rompimento após consolidação observada.
- Preferência por liquidez estável.

Todos devem receber os mesmos dados disponíveis, custos comparáveis e regras de capital explícitas.

Não faça centenas de combinações para depois mostrar somente a melhor.

## 13. Carteiras de pesquisa e portfólio único

Use capital fictício inicial de R$400.

Podem existir carteiras independentes por estratégia e cenário para estudar hipóteses. Entretanto, implemente também um **portfólio único de R$400**, que precisa escolher entre sinais concorrentes.

Esse portfólio deve ter:

- Caixa compartilhado.
- Reserva para ordens pendentes.
- Limites de exposição e posições.
- Deduplicação de exposição ao mesmo mint.
- Política de alocação definida antecipadamente.
- Custos compatíveis com o tamanho das posições.
- Registro das oportunidades recusadas.

Não some lucros de carteiras independentes como se todas usassem os mesmos R$400.

Não escolha retrospectivamente a estratégia vencedora para representar o portfólio.

Use referência cambial identificada, disponível no momento. Diferencie equivalência BRL ao câmbio inicial de conversão ao câmbio atual.

## 14. Simulação financeira realista

Use contabilidade precisa, preferencialmente Decimal para valores monetários relevantes.

Modele:

- Ordens pendentes.
- Latência.
- Entrada em cotação posterior ao sinal.
- Rechecagem antes do fill.
- Quantidade comprada.
- Taxas.
- Spread.
- Slippage.
- Impacto.
- Custos de rede.
- Venda parcial.
- Stop.
- Trailing.
- Saída por tempo.
- Saída por deterioração de condições.
- Falta de liquidez.
- Ausência de saída.

Não preencher no preço do sinal ou na máxima futura.

Stop é gatilho; pode ocorrer fill muito pior após um salto de preço.

Custos embutidos no preço não podem ser descontados novamente do caixa.

Uma posição sem saída válida deve continuar inconclusiva, com capital comprometido. Não classificá-la como empate nem apagá-la.

Separe:

- Caixa.
- PnL fechado.
- Parcial realizada.
- Patrimônio estimado.
- Exposição.
- Custos.
- Posições abertas.
- Posições inconclusivas.
- Estresse de recuperação zero.

## 15. Cenários e hipóteses de entrada/saída

Implemente cenários optimistic, base e adverse, com parâmetros explícitos e versionados.

Pesquise valores plausíveis e documente o que é observado, estimado ou assumido. Não reduza custos para fabricar lucro.

Como hipóteses iniciais, investigue:

- Entrada imediata após elegibilidade.
- Entrada após confirmação.
- Entrada após consolidação.
- Entrada após recuperação de momentum.
- Saída por stop fixo.
- Saída ajustada à volatilidade.
- Saída por perda de momentum.
- Parcial e trailing.

Compare poucas variantes por rodada. Meça tanto perdas evitadas quanto ganhos abandonados.

A política inicial pode usar ordens pequenas em relação ao capital, exposição limitada e take profit parcial. Escolha e registre seus parâmetros antes da validação, sem tratar qualquer conjunto como comprovadamente lucrativo.

## 16. Quotes e viabilidade de entrada/saída

Pesquise integração somente leitura com um provedor oficial/autorizado de quotes.

Quando possível:

- Consulte compra no orçamento pretendido.
- Consulte venda para a quantidade correspondente.
- Registre quantidades atômicas, mints e decimais.
- Registre requested/received timestamps.
- Preserve fees, impacto, rota e validade.
- Identifique ausência de rota.
- Meça deterioração rápida das condições.
- Faça consultas de saída com frequência limitada.

Uma quote de valor pequeno não verifica uma posição maior.

Quote indicativa não comprova execução real. Uma consulta que falhou não equivale a transação enviada.

Se estudar custos de falhas on-chain, use cenários identificados e evidência apropriada. Não invente probabilidades nem debite taxa de rede por um simples erro local de consulta.

Sem fonte ou chave disponível, mantenha a simulação condicional e mostre a limitação.

## 17. Viabilidade econômica para R$400

Calcule o ponto de equilíbrio por tamanho de posição.

Responda:

- Quanto o ativo precisa subir para cobrir entrada e saída?
- Qual parcela do retorno bruto é consumida pelos custos?
- O tamanho pequeno torna a estratégia inviável?
- A frequência de operações aumenta resultado ou apenas custos?
- Quanto custariam dados e infraestrutura?
- A estratégia depende de condições disponíveis somente em um plano pago?
- O ganho esperado continua plausível no adverso?

Inclua custos recorrentes no resultado global sem contá-los repetidamente por operação.

Crie uma regra de **não operar** quando custos, risco ou incerteza não sustentarem a entrada.

Não imponha quantidade mínima de trades por dia.

## 18. Diagnóstico de perdas

Crie um módulo de forensics.

Para cada perda, reconstrua:

- Token/par/modelo.
- Descoberta e primeira observação.
- Alerta, ordem, elegibilidade, entrada e saída.
- Indicadores disponíveis no sinal.
- Movimento anterior ao alerta.
- Movimento durante a latência.
- Evolução da liquidez e atividade.
- Máxima e mínima efetivamente observadas.
- Motivo da saída.
- Resultado bruto, custos e líquido.
- Gaps e informações ausentes.
- Diferença entre stop configurado e fill posterior.

Classifique hipóteses de falha somente com evidência, como entrada tardia, reversão, contração de liquidez, custos excessivos ou falta de saída.

Se a causa não puder ser distinguida, registre unknown.

## 19. Oportunidades perdidas

Crie um módulo para investigar moedas que atingiram +100%, +200% ou +500% sem seleção anterior.

Verifique:

- Quando o sistema descobriu a moeda.
- Quantos snapshots existiam antes da alta.
- Quais scores e critérios foram registrados.
- Primeiro instante tecnicamente elegível.
- Motivo da rejeição.
- Limites de ranking/alerta/capital.
- Existência de preço/liquidez posteriores à latência.
- Disponibilidade de rota.
- Possibilidade de avaliar uma saída.

Diferencie movimentos detectáveis, movimentos anteriores à descoberta, dados insuficientes, ausência de condições financeiras e rejeição pelos critérios.

Não use o resultado futuro para transformar a moeda em compra retroativamente válida.

## 20. Horizontes e comparações justas

Acompanhe horizontes de 5, 15, 30 e 60 minutos, quatro horas e 24 horas, quando a cobertura permitir.

Registre alvos +100%, +200%, +500% e quedas extremas.

Separe:

- Referência da primeira observação.
- Primeiro instante elegível comum.
- Referência do alerta.
- Entrada financeira.
- Saída financeira.

Não compare retornos de referências diferentes como se fossem equivalentes.

Calcule precisão, recall e falsos positivos somente em universos e referências definidos. O recall do universo observado não é recall de todas as meme coins da Solana.

Resultados incompletos devem permanecer visíveis, com análise de sensibilidade à censura.

## 21. Validação científica

Implemente desenvolvimento, validação e teste futuro reservado, com embargo/purga quando necessários.

Registre antecipadamente:

- Regras.
- Features.
- Custos.
- Capital.
- Versão.
- Calendário.
- Métrica principal.
- Baselines.
- Critérios de amostra.
- Comparações planejadas.
- Regra de parada.

Não use o teste final para ajustar parâmetros.

Use métodos que considerem dependência entre tokens, snapshots, cenários e dias. Um token replicado em dez estratégias não vira dez observações independentes.

Mínimos como 100 operações distintas e 20 dias podem servir como filtros preliminares, mas não garantem significância.

Audite a adequação dos intervalos, bootstrap e múltiplas comparações. Não estime quantis extremos com resolução insuficiente e apresente isso como certeza.

Não espere semanas parado para concluir a implementação: entregue a coleta e a avaliação futuras prontas, com comandos e critérios claros.

## 22. Robustez financeira

Mostre:

- PnL líquido.
- Retorno sobre capital.
- Expectativa por operação.
- Ganho e perda médios.
- Taxa de acerto.
- Profit factor.
- Drawdown.
- Exposição.
- Tempo de posição.
- Falhas de entrada/saída.
- Resultado por período e faixa de liquidez.
- Sensibilidade a custos e latência.

Teste a dependência:

- Do melhor ganho.
- Dos três maiores ganhos.
- De um token.
- De um dia.
- De um horário.
- De um cenário favorável.
- Das operações que conseguiram fechar.

Não descarte as piores observações para melhorar a conclusão.

## 23. Experiência de uso no Windows

Quero instalação simples e comandos claros.

Crie launchers como:

- `INICIAR_COLETA.bat`
- `VER_ALERTAS.bat`
- `VER_OPERACOES.bat`
- `VER_RESULTADOS.bat`
- `DIAGNOSTICO.bat`

Eles devem funcionar independentemente do diretório de onde foram abertos, usando a pasta do próprio script.

Evite o erro `No module named meme_research` com estrutura correta, documentação e diagnóstico.

Mostre:

- Versão do programa.
- Interpretador.
- Pasta do projeto.
- Caminho real do banco.
- Módulos habilitados.
- Último ciclo.
- Idade dos dados.
- Último erro.
- Motivo de zero sinais ou operações.

Não crie outro banco vazio silenciosamente por causa do diretório atual.

Mantenha CLI funcional. Implemente e documente comandos equivalentes a:

- `run`
- `watch`
- `health`
- `audit`
- `moonshot`
- `moonshot-alerts`
- `moonshot-trades`
- `moonshot-profitability`
- `moonshot-forensics`
- `moonshot-missed`
- `moonshot-quality`
- `moonshot-compare`
- `evaluate`
- `demo`

Relatórios devem funcionar em outro terminal sem iniciar outro coletor.

## 24. Persistência, falhas e testes

Implemente:

- Migrações versionadas.
- Backup consistente.
- Lock para impedir dois coletores no mesmo banco.
- Transações.
- Idempotência.
- Recuperação após restart.
- Integridade referencial.
- Protocolos e evidências protegidos contra alterações acidentais.
- Relatórios somente leitura.
- Logs sem segredos.

Teste especialmente:

- Informação futura.
- Metadados recebidos tarde.
- Troca de par.
- Duplicação.
- Gaps e stale.
- Falta de preço/liquidez.
- Erros de API.
- HTTP 429.
- Custos duplicados.
- Reserva de capital.
- Sinais concorrentes.
- Stop ultrapassado.
- Ausência de venda.
- Quotes incompatíveis.
- Reinício.
- Migração com falha.
- Teste reservado.
- Caminhos Windows com espaços.

Crie uma demo offline com ganhos, perdas, alta seguida de crash, score alto perdedor, sinal tardio, liquidez insuficiente e posição inconclusiva.

Dados sintéticos devem ficar separados dos dados reais e identificados em todos os relatórios.

## 25. Entrega exigida

Entregue:

1. Projeto completo funcionando.
2. Pesquisa e decisões técnicas com fontes.
3. Moonshot Radar implementado.
4. Simulação financeira e portfólio único.
5. Relatórios de qualidade, perdas e oportunidades.
6. Baselines e protocolo futuro.
7. Testes e logs de execução.
8. Demo sintética.
9. Configuração de exemplo.
10. Launchers Windows.
11. Guia simples de instalação e uso.
12. ZIP extraído e testado em pasta limpa.
13. Lista do que foi validado e do que permanece pendente.

Não alegue teste Windows se executou somente Linux. Não alegue coleta real quando usou fixtures. Não alegue lucro real quando calculou cenários.

Se uma fonte estiver inacessível, prossiga com a implementação e os testes possíveis, registrando a limitação.

## 26. Prioridade final

Trabalhe nesta ordem:

1. Fazer o projeto executar e coletar corretamente.
2. Garantir qualidade temporal e contabilidade.
3. Implementar Moonshot Radar e baselines.
4. Medir custos, atraso e possibilidade de saída.
5. Investigar poucas melhorias de maior valor econômico.
6. Testar em dados futuros com capital comparável.
7. Descartar abordagens sem vantagem sustentada.

Quero que você busque seriamente melhorar a chance de lucro líquido. Cada mudança deve ter uma hipótese, uma medição e uma comparação.

Não altere a definição de lucro para fazer o projeto parecer vencedor. Se a melhor conclusão for não operar, preservar capital ou rejeitar uma estratégia, isso deve aparecer claramente.

Comece agora a pesquisa e a implementação deste projeto do zero, sem exigir arquivos de versões anteriores.