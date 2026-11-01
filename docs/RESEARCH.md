# Pesquisa, evidência e fila inicial

## O que se sabe e o que não se sabe

Não há dataset prospectivo de mercado nesta entrega. Relatos de perdas/ganhos anteriores não são dados de treinamento nem evidência reauditada. Portanto o gargalo econômico dominante é **desconhecido**. A prioridade demonstrável de engenharia é não converter dados ausentes e preços indicativos em fills garantidos. Não há estimativa comprovada de retorno esperado para justificar investimento.

A rodada contém apenas três hipóteses principais. Os baselines não são estratégias escolhidas depois de olhar a demo. Pesos e limites são escolhas explicáveis, não valores otimizados. A fila abaixo é uma priorização inicial por testabilidade/custo, sem inventar tamanho de efeito.

| Prioridade / hipótese | Motivação e mecanismo possível | Evidência disponível | Efeito econômico | Esforço e dados | Teste e refutação |
|---|---|---|---|---|---|
| 1 — C: liquidez/risco/abstenção | Contração e dados insuficientes podem preceder fills piores e impossibilidade de saída | Documentação de fees/hooks e mecânica de AMM; nenhuma amostra prospectiva de vantagem | Desconhecido; reduzir cauda negativa também pode eliminar maiores ganhos | Features públicas, quotes opcionais; integração moderada | C vs A e baselines no mesmo calendário; registrar vencedoras filtradas; rejeitar se retorno líquido não melhorar ou depender de casos censurados |
| 2 — B: continuidade | Passos positivos com atividade persistente podem distinguir continuação de reversão | Hipótese econômica, não comprovação em meme coins | Desconhecido; confirmação pode encarecer entrada | Cinco snapshots, janelas m5 separadas por 300–480 s; baixo custo incremental | B vs aleatório/volume/momentum; rejeitar se vantagem desaparecer em adverso, novos períodos ou sem melhores ganhos |
| 3 — A: momentum inicial | Aceleração em pequena alta pode anteceder continuação em parte do universo observado | Hipótese; descoberta parcial pode chegar tarde | Desconhecido, potencial custo de entrada tardia | Três snapshots com espaçamento mínimo; nenhuma fonte premium obrigatória | A vs baselines, atraso e alta pré-alerta registrados; rejeitar se custos consumirem retorno ou não persistir fora do desenvolvimento |

Antecipar a descoberta por WebSocket foi **adiado**, não rejeitado empiricamente: o feed `logsSubscribe` só entrega logs e exige programa/decoder de pools, recuperação de lacunas e validação. Não fingimos ter isso. Próximo investimento de engenharia só se justifica após medir atrasos/cobertura na coleta atual. Nenhum provedor pago é contratado.

## Fontes efetivamente consultadas

Acesso em 01/11/2026. Foi possível ler os documentos primários via repositório oficial `solana-foundation/solana-com`, commit **b83505d379f083d55560e696765d7d84429e18fa**. Os textos recebidos estão em `evidence/solana-*.txt`.

- [Fees](https://github.com/solana-foundation/solana-com/blob/b83505d379f083d55560e696765d7d84429e18fa/apps/docs/content/docs/en/core/fees/fee-structure.mdx): tarifa por assinatura e prioridade; transações processadas que falham também podem pagar. Uma falha local de HTTP não é uma transação processada. Valores USD dos nossos cenários **não** foram derivados de um preço SOL atual.
- [getMultipleAccounts](https://github.com/solana-foundation/solana-com/blob/b83505d379f083d55560e696765d7d84429e18fa/apps/docs/content/docs/en/rpc/http/getmultipleaccounts.mdx): leitura em lote de contas. O cliente limita a dez contas e 30 tentativas/hora; não usa RPC para negociar.
- [logsSubscribe](https://github.com/solana-foundation/solana-com/blob/b83505d379f083d55560e696765d7d84429e18fa/apps/docs/content/docs/en/rpc/websocket/logssubscribe.mdx): logs não são um feed de pools já decodificados; filtro mentions suporta exatamente um endereço.
- [Transfer fees](https://github.com/solana-foundation/solana-com/blob/b83505d379f083d55560e696765d7d84429e18fa/apps/docs/content/docs/en/tokens/extensions/transfer-fees.mdx) e [transfer hooks](https://github.com/solana-foundation/solana-com/blob/b83505d379f083d55560e696765d7d84429e18fa/apps/docs/content/docs/en/tokens/extensions/transfer-hook.mdx): extensões podem mudar quantidades e permissões. Renúncia de autoridades clássicas não comprova saída. Programas diferentes do SPL clássico são explicitamente não suportados pelo filtro C, quando esse fato está disponível.

## Referências cuja leitura vigente ficou pendente

A rede negou os domínios externos abaixo; `evidence/source_access.json` registra tentativas. As URLs são referências para revisão, **não** alegação de documentação atual lida ou integração validada:

- DEX Screener: https://docs.dexscreener.com/api/reference e https://docs.dexscreener.com/api/api-terms-and-conditions
- Jupiter: https://developers.jup.ag/docs/swap/get-quote — adaptador GET `/swap/v1/quote` opcional; verificar suporte/plano atual antes do uso. Não usa endpoints de execução.
- PTAX: https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/documentacao
- Bailey, Borwein, López de Prado e Zhu, *The Probability of Backtest Overfitting*, Journal of Computational Finance, 2017, DOI 10.21314/JCF.2016.322. Referência bibliográfica relevante ao orçamento limitado de tentativas; texto não consultado nesta instância. Não alegamos reproduzir esse método.
- Künsch, *The Jackknife and the Bootstrap for General Stationary Observations*, Annals of Statistics, 1989. Referência de dependência temporal; não inferimos estacionariedade do mercado a partir dela.

O método implementado é bootstrap por blocos circulares de dias, com família primária registrada, intervalos descritivos, teste de resolução de cauda e sensibilidade de blocos. Isso não substitui mais dias independentes nem valida execução.

## Decisões e próximos experimentos

1. Iniciar coleta real e demonstrar normalização/proveniência em amostra autorizada, sem mudar regras para forçar alertas.
2. Medir descoberta→observação→features→alerta→fill, campos ausentes e frequência de saída válida. Quando criação do token não é conhecida, atraso absoluto de descoberta permanece desconhecido.
3. Capturar quotes indicativas no orçamento real e retorno com a quantidade atômica recebida. Medir idade/deterioração: `quotes` guarda cada tentativa bem-sucedida e sua versão observada; ainda não estima distribuição empírica de execução real.
4. Só após evidência apontar gargalo, registrar nova rodada limitada. Sem vantagem adversa persistente e dados suficientes: manter abstenção.

Descartar a abordagem no cenário adverso por custo acima do limite é uma **decisão do protocolo sob hipóteses**, não prova de que todo o mercado é inviável. Não existem probabilidades de falha inventadas. `failure_every_n` é estresse determinístico, desligado por padrão, e exige protocolo/banco novo.
