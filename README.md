# Sr. Rotas | Coletor do Radar

Coletor independente para normalizar eventos e locais e gerar lotes para a API do Radar. O código, o contrato de integração, os esquemas JSON e os dados fictícios de teste estão em [radar-collector/](radar-collector/).

## Teste local

Com Python 3.10 ou mais recente, execute na raiz do repositório.

```sh
cd radar-collector
python3 -m unittest -v
```

Os testes usam uma API simulada. Para revisar a integração do Admin, consulte o [contrato v1.3](radar-collector/docs/CONTRATO_RADAR_v1.3.md) e o [JSON de exemplo](radar-collector/docs/radar.admin-import.v2.exemplo.json). O [guia do coletor](radar-collector/README.md) explica como gerar os lotes localmente.

O código da tentativa anterior de aplicativo Streamlit permanece na raiz e no histórico do repositório.
