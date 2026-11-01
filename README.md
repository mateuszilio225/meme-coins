# Moonshot Profit Research

Novo sistema Python/SQLite de pesquisa prospectiva sobre tokens Solana, com Moonshot Radar A/B/C, baselines, carteiras condicionais e portfólio único de R$400 fictícios. Não envia transações.

**Comece por [LEIA_PRIMEIRO.md](LEIA_PRIMEIRO.md).** Python 3.11+, sem dependências de execução externas. Versão nova 0.1.1, sem continuidade alegada de código 3.5 não recebido.

- [Pesquisa e prioridades](docs/RESEARCH.md)
- [Contabilidade e viabilidade](docs/ECONOMICS.md)
- [Protocolo congelado](docs/PROTOCOL.md)
- [Arquitetura e fontes](docs/ARCHITECTURE.md)
- [Validações e pendências](docs/VALIDATION.md)
- [Especificação recebida](docs/SPECIFICATION.md)

```sh
python3 -m meme_research demo --output /tmp/moonshot-demo.sqlite
python3 -m unittest discover -s tests -v
```

A demo é sintética, isolada e não comprova vantagem econômica. Toda execução financeira é condicional. A melhor decisão pode ser não operar.
