# Validação e limites

## Implementado e exercitado localmente

Python 3.12.14 / Linux. Sem dependências externas de execução.

- CLI e importação `python -m meme_research`.
- Configuração, capital, custos e calendário validados; protocolo e hash congelados.
- SQLite v1, rollback em migração com falha, backup sem overwrite, lock e read-only.
- Duplicação, restart, histórico isolado por mint/par/fonte e disponibilidade temporal.
- Radar A/B/C e baselines contemporâneos; componentes de score armazenados.
- Carteiras independentes e portfólio único com caixa/reservas compartilhados por cenário.
- Fill posterior à requisição elegível, stop com salto, venda parcial/trailing, risco de liquidez e inconclusivas.
- Equilíbrio de ida e volta validado matematicamente contra a contabilidade.
- Custos globais de infraestrutura sem débito por trade; erros de consulta sem taxa de rede.
- 429 com cooldown persistente; cache não rejuvenesce observações; quote incompatível e transação inesperada rejeitadas.
- Demo com ganhos, perdas, score alto perdedor, liquidez ausente e ausência de saída, sem sobrescrever arquivos.
- Ablações de execução em bancos separados sem mutar fonte; não representam dados prospectivos novos.
- Holdout oculto, avaliação antes do fim recusada, amostra insuficiente e resolução de bootstrap verificadas.
- Relatórios financeiros/qualidade/forensics/oportunidades/scores e auditoria da demo.

Logs efetivamente executados ficam em `evidence/`. A contagem final e o teste da extração limpa constam em `evidence/RELEASE_VALIDATION.json` gerado pelo script de release. Não confundir os números relatados do projeto antigo com esta suíte nova.

## Implementado com testes de contrato; integração externa não validada

| Componente | Evidência local | Limitação externa |
|---|---|---|
| DEX Screener | Parser, normalização e persistência; payloads de teste | Acesso público bloqueado pelo proxy desta instância; contrato vigente/termos ainda exigem conferência |
| BCB PTAX | Cliente com disponibilidade de recebimento e init explícito | Consulta real bloqueada, nenhum FX real obtido |
| Solana RPC | Método de leitura em lote, orçamento e interpretação conservadora | Não houve validação ao vivo do enriquecimento |
| Jupiter | Quote-only, mints/amount/rota, ausência de chave, sem segredos em payload salvo | Sem chave e com rede bloqueada; endpoint/plano/quotes reais não validados |
| Launchers Windows | Paths entre aspas, cd no script, TOML ancorado, CRLF | Não executados em Windows |
| Instalabilidade | Importação local e pacote em pasta limpa, conforme release | Outros interpretadores/SOs sem validação |

## Não implementado / não concluído

- Decoder WebSocket de novos pools e recuperação de eventos: deliberadamente não ativado sem validação.
- Segurança completa Token-2022, holders econômicos, sellability verificada ou detecção de fraude.
- Fills reais, taxas on-chain empíricas, aluguel/criação de contas e estimativa probabilística de falhas.
- Benchmark SOL líquido e classificação validada de regimes.
- Treinamento/calibração probabilística de score; ausência de amostra torna isso injustificado.
- Atribuição causal completa seleção vs descoberta vs saída; forensics distingue fatos contábeis e hipóteses/unknown.
- Validação futura de semanas: o coletor e os gates estão preparados, mas nenhum dia futuro foi fabricado.
- Uma conclusão de vantagem líquida sustentável. **Evidência insuficiente.**

Remoção do melhor/top3 e leave-group-out de mint/dia/hora/faixa de liquidez são descritivos sobre encerradas, acompanhados do resultado global com inconclusivas. O custo de filtros inclui oportunidades observadas recusadas, mas não presume que seriam vendáveis. Não se declara causalidade isolada a partir de carteiras que mudaram composição/capital.

## O que falta para uso de pesquisa ao vivo

1. Na nuvem, revisar/salvar os domínios do rascunho nas configurações e publicar o ambiente. Isso não foi feito pelo agente. No seu Windows, verificar acesso permitido e termos dos provedores.
2. Validar `init --ptax`, depois `run --once`, inspecionar `health` e `moonshot-quality` com dados reais.
3. Se quotes forem necessárias, configurar a chave no ambiente, revisar o endpoint/plano vigente e registrar novo protocolo antes de iniciar essa coleta.
4. Configurar custos recorrentes reais; acompanhar o calendário futuro sem alterar regras após ver resultados.
5. Se dados não sustentarem vantagem, conservar caixa e registrar a tentativa. Nenhum passo autoriza trading real.
