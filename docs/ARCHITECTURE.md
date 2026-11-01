# Arquitetura, persistência e contratos

## Módulos

- `config.py`: validação, caminhos absolutos, serialização canônica, calendário, hash e TOML.
- `store.py`: schema v1, transações, foreign keys, WAL, backup pela API SQLite, lock de processo com fcntl/msvcrt e triggers de imutabilidade.
- `data.py`: HTTP serial, orçamentos persistidos, cache positivo/negativo com timestamp original, cooldown/backoff/jitter/circuit breaker, DEX, RPC somente leitura, PTAX e quotes opcionais.
- `radar.py`: indicadores temporais, componentes de score, riscos, ranking contemporâneo, baselines e todas as decisões.
- `finance.py`: Decimal, reservas, ordens, fills, ledger, capacidade, equilíbrio, partial/trailing, timeout/inconclusivas e snapshots patrimoniais.
- `service.py`: coletor compartilhado, prioridade a posições/ordens e tokens menos recentemente consultados, ingestão e ciclo atômico.
- `reports.py`: relatórios somente leitura, qualidade, perdas, oportunidades, coortes, scores, custos e reconciliação.
- `evaluate.py`: gates de amostra, bloqueio temporal, incerteza por blocos diários e registro append-only de avaliações.
- `ablation.py`: replay de desenvolvimento em três bancos separados, sinais A fixos, alterações isoladas de entrada/saída.
- `demo.py`: fixtures sintéticas explicitamente separadas.
- `cli.py`: comandos, diagnóstico, init explícito e tratamento de interrupção/erros.

## Schema e segurança operacional

Observações, protocolos, decisões, alertas, fills, ledger, fatos, quotes, avaliações, eventos e curvas patrimoniais são append-only com triggers contra update/delete. Ordens/posições/caixa são projeções mutáveis auditáveis contra fills/ledger. Isso previne acidentes, não alterações maliciosas por um administrador do arquivo.

Um ciclo inteiro é transacional: observações e transições financeiras são revertidas juntas se ocorrer uma falha. WAL permite relatórios em outro terminal. Há idempotência na chave mint/par/fonte/requisição/fingerprint e nos alertas por mint/modelo/período. Não há recuperação de um POST de transação real porque não existe tal operação. Se uma requisição externa terminou e o ciclo caiu antes de commit, a observação ainda não foi consumida: na próxima coleta terá outro timestamp de recebimento, sem alerta fabricado no passado.

A migração v1 é idempotente e recusa schema desconhecido. Migração explícita de arquivo preexistente vazio gera backup; bancos externos com tabelas não são convertidos. O backup usa SQLite backup API e destino exclusivo. O lock é um lock do sistema operacional, liberado ao morrer o processo; arquivo `.lock` remanescente não significa processo vivo.

Relatórios recusam abrir banco inexistente, em vez de criar outro silenciosamente. Paths relativos são ancorados no TOML. `run` não aceita uma demo como banco de coleta real. A categoria de replay aparece nos relatórios e nunca substitui um protocolo prospectivo.

## Fontes e fila

O feed público previsto é `token-profiles/latest/v1`, amostra parcial de perfis, não novos pools de toda a rede. Para cada mint, `token-pairs/v1/solana/{mint}` preserva as pools de base token correspondente. Preço USD de uma pool não é combinado com liquidez de outra. Descobertas são deduplicadas pelo mint; observa-se apenas o número limitado pelo orçamento. Prioridade a posições/ordens abertas, depois a menor `last_poll`; sob saturação o sistema pode não cumprir o intervalo nominal. Isso deve aparecer em gaps/idade de dados.

Orçamentos conservadores: perfis 2/minuto com cache 300 s; pares 12/minuto e cache 25 s; RPC 30/hora; quotes 6/minuto; PTAX 2/minuto. Não são alegações de limite contratado do fornecedor. Concorrência HTTP = 1. Cada tentativa real consome orçamento; cache/deferral não o consome. Status HTTP, endpoint sem query, requested/received e estado são persistidos. Resposta tem limite de 2 MB, JSON com rejeição de NaN e sem redirects. Timeout 10 s. 429 respeita Retry-After e próximo ciclo; falhas repetidas abrem cooldown mínimo de 300 s. Sem rotação de endpoint/IP/chave.

Cache nunca ganha timestamp novo ao ser lido. Dados em cache não geram nova observação de mercado. Não existe retry imediato em 429. Nunca se imprime cabeçalho, chave ou ambiente. HTTP usa TLS e proxies herdados, sem desabilitar verificação.

## Tempo e dados ausentes

Cada observação guarda requisição, recebimento, timestamp efetivamente fornecido, preço, liquidez/volume/contagens, criação do par, fonte, qualidade, raw e fingerprint. O parser deixa timestamp de preço do provedor indisponível quando a fonte não o fornece. Isso impede alegação de frescor garantido; `require_provider_timestamp=true` pode intencionalmente impedir todas as entradas.

Requisição deve ocorrer depois do sinal + latência para fill. Metadados só chegam às features de observações posteriores à disponibilidade. Trocar pool ou fonte reinicia a referência/história daquela série. Um snapshot atual não comprova que o token nasceu naquele instante.

## Quotes e riscos conhecidos

O adaptador quote-only usa GET Jupiter `/swap/v1/quote`, opcional, com cabeçalho local de chave. A ausência de chave faz zero chamadas. Respostas de mints/amount incorretos, sem rota e com campo de transação inesperado são recusadas; campos inesperados e payload de transação não são retidos. O retorno de compra fornece quantidade atômica usada no reverse quote, sem adivinhar decimais do token. USDC usa seis casas por definição do mint conhecido; equivalência USDC/USD é condicional ao peg.

A quote consulta orçamento exato, mas o simulador continua a usar seu modelo independente de preço/impacto; não se alega que a quantidade simulada corresponde à quantidade executada on-chain. Quotes não integram execução verificada. Não há validação completa de extensões, transferência, holders econômicos, preço SOL atual, prioridade empírica ou aluguel/criação de contas. Custos extra não modelados continuam limitação econômica explícita. O enriquecimento opcional assinala programa diferente do SPL clássico como não suportado para C quando observado.

## Reprodução e auditoria

`audit` reconcilia caixa contra ledger e quantidades contra fills, verifica foreign keys, integridade e hash do protocolo. Os testes exercitam cenários de perda, gaps e falhas; não certificam tokens ou ausência total de bugs. A demo é determinística e não calibra regras. `ablate` captura snapshot SQLite somente leitura do desenvolvimento, preserva sinais e publica hash do conjunto utilizado, com nova categoria e novos arquivos.
