# Coletor do Radar | Sr. Rotas

Coletor independente em Python 3.10+ para normalizar eventos e locais e gerar lotes para a API V2 do Radar. O contrato do importador administrativo usa `radar.admin-import.v2` e aceita arquivos v1 conforme o esquema anterior.

## Teste local

Execute na raiz do repositório.

```sh
python3 -m unittest -v
python3 collector.py build --source teste_sp --events-html fixtures/agenda.html --pois-csv fixtures/locais.csv --out saida-teste
```

No Windows, use `py -3` no lugar de `python3`, se necessário. Os testes usam um servidor simulado em loopback e exemplos fictícios. O comando `build` grava os lotes e um relatório em uma pasta nova. Os lotes da API usam `run_id`. O arquivo para a prévia do Admin usa `batch_id`.

## Integração com o Admin

Use o [contrato v1.3](docs/CONTRATO_RADAR_v1.3.md), o [esquema v2](docs/radar.admin-import.v2.schema.json) e o [exemplo fictício](docs/radar.admin-import.v2.exemplo.json) no ambiente local da equipe. Em uma base vazia, o exemplo prevê seis itens prontos, um duplicado e um pendente. A capa fictícia fica aguardando conferência.

## Piloto pela API

Após o teste local, a equipe define a URL e a fonte autorizada do piloto e provisiona a chave individual. Configure `SR_ROTAS_BASE_URL` e `SR_ROTAS_COLLECTOR_KEY` no Dell. Use `python3 collector.py ping` e, com dados reais autorizados, `python3 collector.py send <arquivo-de-lote>` para validar com `dry_run`. O envio autorizado à revisão exige `--submit`. Para repetir uma tentativa de envio, preserve o arquivo original e o comando.

As credenciais ficam no ambiente do Dell. A pasta `fixtures/` contém somente exemplos fictícios.
