# Moonshot Profit Research 0.1.0

**Projeto novo de pesquisa e dinheiro fictício. Não é a antiga versão 3.5. Não há vantagem econômica comprovada.** Não conecta carteira, não assina e não envia transações. Preços e quotes não garantem execução. Nenhum resultado da demo comprova lucro.

## Começar no Windows

1. Instale Python **3.11 ou superior**, com o launcher `py`.
2. Extraia **todo** o ZIP, por exemplo em `C:\Bots\moonshot_profit_research`. A pasta correta contém `config.toml`, `meme_research` e os `.bat`. Não execute dentro do ZIP.
3. Abra `INSTALAR.bat`. Não é preciso baixar bibliotecas para executar: usa apenas a biblioteca padrão.
4. Primeiro experimente a demo abaixo. Para coleta real de dados, abra `INICIALIZAR.bat`: ele consulta PTAX e congela as regras, o câmbio identificado e o calendário no banco. Falha de fonte é um erro explícito; não inventa câmbio.
5. Abra `INICIAR_COLETA.bat`. Mantenha esse terminal ativo para coletar. Use os outros launchers em terminais separados.

O programa **não negocia**, mesmo que o radar emita alertas. O portfólio principal começa sem operar se não houver quotes indicativas no tamanho exigido. As carteiras condicionais de pesquisa têm suposições de execução diferentes e ficam identificadas.

### Demo offline, antes de usar APIs

No CMD aberto na pasta do projeto:

```bat
py -3 -m meme_research demo --output "data\demo.sqlite"
py -3 -m meme_research --config "data\demo.toml" health
py -3 -m meme_research --config "data\demo.toml" moonshot-profitability
py -3 -m meme_research --config "data\demo.toml" audit
```

A demo recusa sobrescrever arquivos existentes. Para repetir, use outro nome. O TOML gerado aponta para o caminho absoluto do banco da demo; ao mover essa demo para outra máquina, ajuste somente esse caminho ou gere outra demo. Dados reais usam `config.toml` e banco separado.

### Coleta de dados públicos

```bat
py -3 -m meme_research init --ptax
py -3 -m meme_research run --once
py -3 -m meme_research run
```

`init` é explícito e não reinicia uma pesquisa existente. Nunca copie um banco de demo sobre o real. A inicialização não cria operações. Se PTAX falhar, tente novamente após resolver acesso/serviço. Como alternativa, configure em `config.toml` os campos `fx_brl_per_usd`, `fx_source`, `fx_available_at` com uma referência real verificável disponível antes do registro; depois execute `init` sem `--ptax`. `fx` consulta PTAX e mostra os campos, sem iniciar uma pesquisa. Não use o câmbio fictício da demo em dados reais.

O banco real é resolvido **em relação à pasta do TOML**, nunca ao diretório atual. Usar `py -m` diretamente de fora da pasta exige instalação do pacote ou voltar à raiz. Os launchers fazem isso automaticamente com `cd /d "%~dp0"`.

O protocolo congela todos os parâmetros financeiros e de pesquisa. Alterações posteriores em `config.toml` impedem `run`. Para uma hipótese nova, preserve o banco anterior e use outro TOML/caminho de banco. A referência PTAX obtida em `init --ptax` é reutilizada automaticamente quando o TOML mantém os campos de FX em zero/vazio.

### Relatórios

```bat
py -3 -m meme_research health
py -3 -m meme_research moonshot
py -3 -m meme_research moonshot-alerts
py -3 -m meme_research moonshot-trades
py -3 -m meme_research moonshot-profitability
py -3 -m meme_research moonshot-forensics
py -3 -m meme_research moonshot-missed
py -3 -m meme_research moonshot-quality
py -3 -m meme_research moonshot-compare
py -3 -m meme_research moonshot-scores
py -3 -m meme_research economics
py -3 -m meme_research audit
py -3 -m meme_research backup --output "backup_novo.sqlite"
```

Os relatórios abrem o banco somente para leitura. `watch --follow` atualiza a visualização sem iniciar outro coletor. A tela limita os alertas apresentados; o banco preserva todas as decisões. Relatórios JSON têm unidades e modo de dados explícitos. `moonshot-compare` compara carteiras independentes; **não soma seus lucros**. Para comparação justa, compare `main` com `main_random` e caixa, ou A/B/C com os baselines condicionais. As classes de execução não são equivalentes.

`health` mostra interpretador, versão, raiz, caminho do banco, último ciclo/erro e idade dos dados. Zero operações pode resultar de abstenção correta. `moonshot-quality` mostra causas dos bloqueios. A API de perfis não cobre todos os lançamentos e não há detecção garantida em segundos.

### Pesquisa futura

```bat
py -3 -m meme_research evaluate --period development
py -3 -m meme_research evaluate --period validation
py -3 -m meme_research evaluate --period test
```

A avaliação exige fim do período. Validação/teste permanecem ocultos nos relatórios até o fim do respectivo intervalo. Não use o teste para alterar regras. Leia [o protocolo](docs/PROTOCOL.md).

```bat
py -3 -m meme_research --config "data\demo.toml" ablate --output "data\ablacao_demo"
```

Ablação lê somente desenvolvimento e cria três bancos novos: referência, entrada confirmada e saída por momentum. Usa os sinais A já registrados, sem retroativamente transformá-los em sinais novos. Isso mede execução, não vantagem futura. Não sobrescreve o histórico.

## APIs opcionais e custos

DEX Screener e PTAX são as fontes públicas previstas. RPC é opcional e desligado; o enriquecimento de autoridades não verifica holders econômicos nem venda. Quotes Jupiter são opcionais e desligadas: configure `quotes_enabled=true` **antes do init** e forneça `JUPITER_API_KEY` no ambiente local. Nunca envie a chave em conversa ou a grave no TOML. O adaptador só faz GET de quote, sem criação de ordem real/execução. Endpoint e autorização precisam de validação externa; veja [VALIDATION](docs/VALIDATION.md).

Configure custos mensais reais de infraestrutura/dados e `monthly_costs_confirmed=true` antes do registro. Zero por padrão significa **não confirmado**, não promessa de custo zero. O relatório debita custos uma vez por carteira contrafactual, proporcionalmente ao tempo, não por trade. Consulte os [limites econômicos](docs/ECONOMICS.md).

## Testes e limites desta entrega

```bat
py -3 -m unittest discover -s tests -v
```

Testado nesta entrega em Linux/Python 3.12.14. **Windows e operações em APIs com chave não foram testados.** Há coleta e simulação implementadas, mas integração pública ponta a ponta ficou bloqueada pela rede do ambiente de construção. Não alegamos lucro, cobertura total, segurança dos tokens ou execução real. Consulte a matriz completa em [VALIDATION](docs/VALIDATION.md).
