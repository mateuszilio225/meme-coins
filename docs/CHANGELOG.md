# 0.1.1 — consulta PTAX

Relato externo: init --ptax retornou HTTP 400 no Windows. Isso comprova que a requisição foi recusada, não identifica sozinho a causa.

Mudança: aliases explícitos `@dataInicial`/`@dataFinalCotacao`; remoção de `$orderby` e `$top`; seleção local da maior dataHoraCotacao. Intervalo continua limitado a dez dias. Validação de timestamp (horário BCB sem fuso interpretado como UTC−3), ausência, taxas inválidas, dados antigos/futuros e paginação não resolvida. Nunca gera câmbio sintético como fallback.

Há nove testes adicionais de regressão PTAX e um diagnóstico público independente, DIAGNOSTICAR_PTAX.py. Não altera schema, políticas financeiras, custos, capital, calendários ou resultados anteriores. Atualizar código preservando config.toml e data.

A integração ao vivo continua não validada nesta nuvem devido a bloqueio de rede. O ajuste não constitui confirmação de que todo HTTP 400 foi resolvido. Se persistir, o diagnóstico deve fornecer a mensagem pública do BCB antes de nova alteração.
