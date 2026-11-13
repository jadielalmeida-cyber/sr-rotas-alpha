# Sr. Rotas | Contrato de integração do Radar

**Versão 1.3 · 13/11/2026 · Referência para integração**

**O fluxo principal é importar vários locais e eventos de uma vez.** O operador fornece o endereço de um site que reúne várias páginas, links de vídeos com dicas de locais, legendas, transcrições ou anotações. A IA extrai e organiza os dados em um único arquivo JSON. O operador sobe o arquivo em **Admin → Radar → Importar JSON**, confere a prévia e confirma os itens válidos em lote. A coleta automática no Dell continua disponível para fontes autorizadas. A referência técnica é a API V2 de coletor externo do Radar. O protótipo deste pacote gera lotes nesse formato e foi testado com um servidor simulado.

## 1. Acesso e permissões

**A chave atual já é suficiente para enviar eventos e propor locais de uma fonte autorizada.** O formato `srrk_<prefixo>_<segredo>` e os escopos V2 atendem à integração. A instância desenvolvedora deve configurar as identidades, as fontes autorizadas e os limites no Admin existente.

| Entrada | Identidade | O que pode fazer |
| --- | --- | --- |
| Importação de JSON curado | Sessão administrativa existente | Validar, importar e revisar um arquivo inteiro, com opção de corrigir ou excluir itens na prévia. |
| Coletor no Dell | Chave individual, vinculada a um coletor e a uma lista explícita de fontes | `events:ingest` para enviar, atualizar e cancelar eventos de sua fonte. `pois:propose` para propor e atualizar locais de sua fonte. Habilitar apenas os escopos usados. |
| Endereço avulso | Sessão administrativa existente | Informar um local pelo formulário **Adicionar endereço** e enviá-lo à mesma revisão. |
| Preparação com IA | Links e materiais fornecidos pelo operador | Extrair candidatos e evidências, montar o JSON e sinalizar pendências. A IA entrega o arquivo ao operador. |

A chave do Dell só fica no ambiente do processo ou em cofre local, como `SR_ROTAS_COLLECTOR_KEY`. A URL do ambiente fica em `SR_ROTAS_BASE_URL`. O Admin cria, gira e revoga a chave. A rotação conserva o ID do coletor e a propriedade dos registros. Informar validade, escopos, fontes e limites ao entregar a credencial, por canal seguro. Emitir chaves distintas por ambiente. A sessão administrativa fica com o operador e `RADAR_INGEST_SECRET` permanece interno ao servidor.

As fontes `manual`, `admin`, `internal` e `ticketmaster` são reservadas no V2. A chave de coletor valida a conexão e envia lotes. Consulta administrativa, aprovação e despublicação exigem a sessão do Admin. Para cada fonte automatizada, designar um único coletor como responsável pelas atualizações. Ao usar curadoria para corrigir um registro do Dell, trabalhar sobre o registro existente pelo Admin. Preservar sua identidade e rastrear a correção.

## 2. Como cada entrada funciona

### Importação em lote no Admin

1. O operador reúne uma ou mais entradas. Um site agregador pode apontar para várias páginas permitidas. Um vídeo pode indicar vários locais. Se a fala ou a legenda não estiver disponível a partir do link, o operador pode fornecer a transcrição, legenda ou as anotações correspondentes. Uma anotação sobre um local conhecido também entra por esse fluxo.
2. A IA entrega um arquivo JSON com todos os candidatos e a evidência de cada um. Para páginas, guardar o link específico do item quando disponível. Para vídeos, guardar o link e o minuto aproximado quando identificável. Para anotações próprias, registrar a data e a descrição da evidência. Identificar a página original do organizador quando ela for usada para confirmar uma dica.
3. O Admin recebe o arquivo, valida o formato e mostra uma prévia com totais de **prontos**, **possíveis duplicatas** e **pendentes**, com motivo por item. Os prontos podem ser enviados em uma ação de lote. Os demais ficam disponíveis para correção ou exclusão seletiva, sem redigitar os registros prontos.
4. A confirmação grava os itens válidos como candidatos e devolve um recibo com o ID do lote, os IDs gerados e o resultado por item. A revisão editorial pode aprovar vários candidatos elegíveis em uma única ação, com opção de excluir itens da seleção. O servidor registra a decisão e a versão de cada candidato. Os registros pendentes de revisão ficam fora do Radar.

### Endereço avulso no Admin

Em **Admin → Radar → Lugares**, adicionar o botão secundário **Adicionar endereço**. Campos da tela: nome, categoria, endereço, cidade, UF, coordenadas e fonte opcional. Preencher São Paulo e SP como valores iniciais editáveis. Se houver geocodificador configurado, sugerir o ponto e exigir confirmação no mapa. Se o endereço for ambíguo ou a busca falhar, permitir ajustar o pino ou informar as coordenadas. O endereço sozinho, sem ponto confirmado, fica na tela como pendência. Para um local conferido em campo sem link, pedir uma nota breve. O servidor registra a data e o operador.

Ao salvar, o Admin converte o formulário em um lote de um POI, com UUID gerado pela aplicação e evidência de página ou nota. Aplicar a mesma validação, verificação de duplicatas e fila de revisão da importação. Um envio válido cria um candidato inativo. A ação principal da interface continua sendo **Importar JSON**, com importação e aprovação em lote.

### Coleta automática no Dell

Usar o coletor deste pacote como cliente inicial ou reaproveitar a implementação interna do projeto após compará-los. Rodar no Dell com um adaptador por fonte, começando por um feed autorizado em São Paulo. Cada adaptador entrega dados no formato V2. O cliente valida os campos, separa registros incompletos, gera lotes e guarda localmente o arquivo enviado e o recibo. A chave autoriza o envio à fila de revisão.

A primeira homologação é sob demanda. O agendamento no Dell começa depois que a fonte, o envio e a revisão forem validados. Configurar a frequência por fonte e usar `America/Sao_Paulo` na operação. Um evento que desaparece de uma página ou de um lote parcial mantém seu estado. Cancelamento automático só pode partir de indicação explícita em fonte estruturada confiável e com identidade confirmada. Quando o V2 aceita `status: cancelled`, o evento sai da exibição imediatamente.

### Curadoria semanal assistida por IA

A curadoria pode rodar semanalmente e produzir o mesmo JSON de importação. Uma dica de restaurante, arena ou outro endereço vira candidato a local permanente. Um anúncio com ocorrência e horário verificáveis vira candidato a evento. Endereços, datas, coordenadas e identidades ambíguas ficam pendentes de confirmação. O revisor trata as exceções e confirma em lote os itens prontos. Cancelamentos sugeridos pela IA exigem conferência humana antes do envio.

Para páginas que bloqueiam rastreamento automatizado, manter a coleta direta desativada. A curadoria usa material obtido e reutilizado de forma autorizada. Um feed ou uma API fornecida pelo responsável pode ser habilitado de acordo com as condições de acesso. O SP Mais Cultura é candidato e bloqueia robôs genéricos no `robots.txt` consultado em 13/11/2026. A frequência semanal é de curadoria. Atualizações urgentes, como cancelamentos de eventos próximos, podem ser registradas manualmente.

## 3. Padrão definido para o JSON administrativo

O formato de implementação é **`radar.admin-import.v2`**. O arquivo [radar.admin-import.v2.schema.json](radar.admin-import.v2.schema.json) define a estrutura e [radar.admin-import.v2.exemplo.json](radar.admin-import.v2.exemplo.json) contém um lote fictício de homologação. O Admin aceita também o esquema [radar.admin-import.v1.schema.json](radar.admin-import.v1.schema.json). Validar cada arquivo pelo esquema correspondente, preservar sua versão no recibo interno e aplicar os ícones por categoria às duas versões.

| Campo | Formato e regra |
| --- | --- |
| `schema_version` | Obrigatório. Valor literal `radar.admin-import.v2` nos arquivos novos. Arquivos `radar.admin-import.v1` seguem válidos pelo esquema anterior. |
| `batch_id` | Obrigatório. UUID v4 em minúsculas. Gerado na preparação do arquivo e preservado durante prévia e reenvio da confirmação. |
| `events`, `pois` | Duas listas obrigatórias. Uma pode ficar vazia. Pelo menos uma contém itens. Aceitar até 500 por lista e até 2.000.000 bytes no arquivo UTF-8. |
| `client_ref` | Identificador obrigatório de cada item dentro do lote, único entre as duas listas. Preservar durante correções de prévia. |
| `evidence` | Lista obrigatória de 1 a 10 evidências. `web` e `video` exigem URL HTTP(S) absoluta. Para `video`, `timestamp_sec` é opcional e inteiro a partir de zero. `note` exige texto e `observed_at` com fuso. Usar `observed_at` apenas quando a evidência foi efetivamente observada. |
| `origin_ref` | Opcional. Objeto com `source` e `external_id` quando a fonte oferece identidade estável. Serve para comparar com registros existentes. Preservar o ID da ocorrência para eventos recorrentes. |

| Tipo | Obrigatórios no arquivo, além dos campos comuns | Necessários para confirmar a ingestão | Opcionais |
| --- | --- | --- | --- |
| Evento | `name` | `starts_at`, `lat`, `lng` | `event_type` (padrão `event`), `expected_end_at`, `venue_name`, `address`, `city`, `state`, `origin_ref`, `cover_image` (v2) |
| Local permanente | `canonical_name` | `poi_type`, `lat`, `lng` | `address`, `city`, `state`, `origin_ref` |

Omitir campos desconhecidos. Coordenadas são números WGS84. Horários usam data e hora ISO 8601 com segundos e fuso explícito. Aceitar `Z` ou offset como `-03:00`. Se informado, o fim deve ser igual ou posterior ao início. Quando omitido, aplicar a estimativa existente do Radar. O tipo de evento usa a enumeração V2. O tipo de local usa o slug aceito pelo Radar, por exemplo `arena` ou `restaurant`. O formulário avulso pede endereço. No arquivo, um local com coordenadas verificadas pode entrar com o endereço ainda ausente.

### Prévia, confirmação e recibo

Usar a sessão administrativa e as verificações de autorização já presentes no projeto. Implementar as operações na área administrativa do Radar. Os caminhos abaixo são o contrato de implementação para o Admin Web.

| Método e caminho | Corpo da requisição ou resultado |
| --- | --- |
| `POST /api/v1/admin/radar/imports/preview` | Recebe o objeto do arquivo como JSON. Retorna `batch_id`, `preview_digest` e `items` com `client_ref`, `state`, `issues` e, quando aplicável, `media_warnings`. Gera prévia sem criar candidatos. |
| `POST /api/v1/admin/radar/imports/confirm` | Recebe `batch` (o mesmo objeto), `preview_digest` e `selected_refs` (lista não vazia de referências distintas em estado `ready`). Retorna o recibo persistido. |
| `GET /api/v1/admin/radar/imports/{batch_id}` | Devolve o recibo administrativo persistido para esse lote. |

1. Validar o envelope, o tamanho do arquivo e o `schema_version`. Na confirmação, aplicar o limite ao JSON de `batch` e admitir o espaço adicional necessário para o digest e a seleção. Envelope inválido retorna HTTP 400, versão incompatível retorna 422 e corpo acima do limite retorna 413. O servidor valida cada item com a definição correspondente do esquema. Erros por item aparecem na prévia com `path` em JSON Pointer e `code`, e permitem aproveitar os demais. Validar também a sintaxe real de datas e URLs. URLs de evidência com credenciais são inválidas. O importador registra o endereço de origem como dado e o apresenta como link.
2. A prévia retorna `ready`, `duplicate`, `pending` ou `invalid`. Usar `missing_required` para campo necessário à ingestão, `invalid_field` para valor inválido, `duplicate_client_ref` para referências repetidas e `possible_duplicate` para coincidências de identidade ou conteúdo. Em item com referência inválida ou ausente, identificar o erro pelo `path`. Coordenadas ausentes, categoria de local ausente ou início ausente deixam o item pendente. O operador pode corrigir na prévia e reenviar à validação, ou seguir com o lote de itens prontos.
3. Conferir duplicatas contra ativos, inativos e o próprio lote. Priorizar `origin_ref` exato quando conhecido. Para similaridade, usar os sinais do Radar, como nome normalizado com endereço ou ponto próximo para locais e nome, local e horário para eventos. Dentro do lote, se os dados do evento ou local forem idênticos, desconsiderar diferenças em `client_ref` e nas evidências para a detecção de duplicata. Manter a primeira ocorrência como candidata, apontar as demais para sua referência e permitir reunir suas evidências na prévia. Em conflito de conteúdo, sinalizar para revisão. Um vínculo com registro existente é decisão explícita no Admin e preserva sua identidade.
4. O `preview_digest` é opaco para o cliente e vincula o conteúdo à prévia e à identidade do operador. Na confirmação, conferir o digest, revalidar a seleção e verificar novamente duplicidade. Se a prévia estiver vencida ou houver conflito novo entre prévia e confirmação, retornar 409 e pedir nova prévia. Persistir candidatos e recibo na mesma transação, com unicidade do `batch_id` para proteger confirmações concorrentes. Se o lote já foi confirmado, retornar o mesmo recibo para o mesmo conteúdo e o mesmo conjunto de referências, mesmo com o digest vencido. Para comparar, canonicalizar a ordem das propriedades do JSON e ordenar as referências selecionadas. A ordem dos itens nas listas do lote faz parte do conteúdo. Mudança após a confirmação exige um novo `batch_id`. O recibo contém `batch_id`, `status: "imported"`, `imported_at` e `items` com `client_ref`, `record_type` (`event` ou `poi`), `record_id` e `status: "pending_review"`.
5. O servidor atribui identidade interna estável por `batch_id` e `client_ref`, registra o operador autenticado e preserva `origin_ref` e a evidência. Reaproveitar os modelos e a revisão do Radar. Mapear a primeira URL de evidência para `source_url` quando existir. A evidência exclusivamente em nota é válida pela via administrativa. O campo `source` e os estados do registro são controlados no servidor. Um POI nasce inativo e um evento nasce pendente de revisão. A ação de aprovação em lote usa as mesmas regras de elegibilidade, controle de versão e auditoria da revisão atual, com resultado por item.

### Resultado esperado com o exemplo fornecido

Com a base de homologação vazia, a prévia mostra **seis prontos, um possível duplicado e um pendente**. `local-03` aponta para `local-01` e `local-04` fica pendente por coordenadas ausentes. A imagem de `evento-01` fica aguardando conferência. Seu link fictício serve só para validar o arquivo. Confirmar os seis itens prontos deve criar seis candidatos e um recibo. Repetir a confirmação deve devolver os mesmos IDs. Após a aprovação dos dados, conferir os ícones de hotel, rodoviária, centro empresarial e show e testar o evento com uma capa de homologação aprovada separadamente.

## 4. Ícones de contexto e capa de evento

### Ícones automáticos

Cada registro recebe um ícone a partir de `poi_type` ou `event_type`. Aplicar o mesmo significado na prévia do Admin e no Radar Android. Reusar os desenhos vetoriais já existentes na vc114. Para centro empresarial, acrescentar um ícone de edifício comercial na mesma família visual.

| Registro | Categoria do JSON | Ícone | Rótulo |
| --- | --- | --- | --- |
| Local | `hotel` | Cama | Hotel |
| Local | `bus_terminal` | Ônibus | Rodoviária |
| Local | `business_center` | Edifício comercial | Centro empresarial |
| Local | `airport` | Avião | Aeroporto |
| Local | `mall` | Sacola | Shopping |
| Local | `hospital` | Cruz | Hospital |
| Local | `arena`, `stadium` | Grupo | Local de eventos |
| Local | `restaurant` | Talheres | Gastronomia |
| Evento | `music` | Nota musical | Show |
| Evento | `sports` | Troféu | Esporte |
| Evento | `theatre` | Ingresso | Teatro |
| Evento | `fair_convention` | Estande | Feira |
| Evento | `cultural`, `family` | Grupo | Cultura, Família |
| Demais | Categoria sem mapeamento | Marcador para local, grupo para evento | Local, Evento |

Reaproveitar também as categorias já reconhecidas pelo app. Dar precedência às chaves exatas da tabela sobre as regras de apelidos. `business_center` é um valor de `poi_type` no formato slug. A categoria representa o contexto do registro. O cálculo de incidência segue usando as observações do Radar. Usar o rótulo acessível junto do ícone e preservar a leitura de horário, endereço e janela de saída.

### Capa opcional de evento em lote

Na versão 2, cada objeto em `events` pode trazer **uma** `cover_image`, vinculada ao seu próprio `client_ref`. Cada item do mesmo JSON pode referenciar uma imagem diferente. O objeto aceita uma das formas abaixo.

| Forma | Campos | Comportamento |
| --- | --- | --- |
| Imagem já cadastrada | `asset_id` | UUID de uma imagem no armazenamento gerenciado pelo projeto. Validar tipo e permissão de uso no evento. |
| Imagem encontrada na fonte | `image_url`, `source_page_url` e, quando disponíveis, `credit` e `usage_reference` | URLs HTTPS da imagem e da página de divulgação. Guardar crédito e a referência de licença, autorização ou condições de reutilização para conferência editorial. |

Ao preparar um lote de fontes fornecidas pelo operador, a IA pode preencher o link da imagem encontrada e a página de origem. Usar material com permissão de reutilização aplicável ou fornecido para esse uso. A página de divulgação ajuda a localizar a fonte da arte. A revisão registra a permissão de uso e o crédito quando aplicável. Uma imagem pode ser vinculada após a importação pelo mesmo controle de capa do Admin.

**O processamento da capa é independente da ingestão dos dados.** Na prévia, validar o campo da capa separadamente. Erros restritos a `cover_image` aparecem como avisos de mídia com o caminho do campo. Na v2, validar primeiro o evento sem `cover_image` e validar a capa em separado pela definição `$defs.cover_image` do mesmo esquema. Um erro isolado nesse campo não muda o estado do evento para seleção. Na v1, a regra de campos do esquema original se aplica. Na confirmação, importar os dados válidos e registrar a referência de capa estruturalmente válida para conferência. Uma referência inválida fica de fora da fila de mídia e seu aviso aparece em `items[].media_warnings` no recibo. Cada aviso contém `path` em JSON Pointer e `code`, como `invalid_cover_image`. O digest e o reenvio idempotente consideram o conteúdo original do lote, inclusive a referência de capa. O Admin mantém o vínculo com o `record_id` do evento e exibe o estado da capa, inclusive se ficar pendente, for recusada ou falhar. A publicação do evento e a aprovação da capa são decisões separadas. O Admin registra a decisão sobre a capa e mostra os estados `pending`, `processing`, `approved`, `rejected` e `failed`. Apenas uma imagem aprovada e processada fica elegível para exibição.

**Busca e armazenamento.** A prévia guarda os links como texto e usa apenas imagens já gerenciadas para miniaturas. Após conferência de uso, um serviço de mídia pode buscar a imagem em domínios habilitados para o projeto. Validar esquema, host e destino público, sem redirecionamentos automáticos, e bloquear credenciais e endereços internos. Validar bytes, formato e dimensões, limitar o download e decodificar e regravar como imagem estática. Para o piloto, aceitar JPEG, PNG e WebP estático de até 5 MB e 16 megapixels, com miniatura de até 640 px no lado maior. Reusar o armazenamento gerenciado disponível no projeto e publicar apenas a referência da imagem processada. Reenvios do lote não duplicam vínculos ou tarefas. A retirada da capa mantém o evento visível pelo ícone.

**Exibição no Radar.** O backend expõe a miniatura gerenciada e o crédito da capa aprovada como dados opcionais do evento. O Android usa o ícone de categoria como padrão e mostra a miniatura quando estiver disponível. Capa pendente, recusada, removida ou com falha de carregamento resulta em exibição pelo ícone. O arquivo JSON carrega referências e metadados. A imagem binária trafega pelo serviço de mídia.

## 5. Comunicação do coletor Dell com o backend

Rodar o primeiro teste com o servidor simulado incluído neste pacote e validar o importador na instância local de desenvolvimento. Para o piloto real, configurar a origem HTTPS aprovada pelo responsável pelo Radar. Chamadas externas usam HTTPS com `Authorization: Bearer <chave individual>`. Os POSTs usam `Content-Type: application/json`.

| Método e rota | Corpo ou resultado esperado |
| --- | --- |
| `GET /api/v1/radar/collector/ping` | Confirma a chave, os escopos, as fontes e os limites. |
| `POST /api/v1/radar/ingest` | Objeto com `run_id`, `dry_run` e lista `events`. Escopo `events:ingest`. |
| `POST /api/v1/radar/collector/pois` | Objeto com `run_id`, `dry_run` e lista `pois`. Escopo `pois:propose`. |

**Evento** tem `source`, `external_id`, `name`, `lat`, `lng`, `starts_at` com fuso explícito e `source_url`. Usar ID estável por ocorrência. Incluir tipo, endereço, local e horário de fim quando a evidência permitir. O V2 trata o fim ausente como estimativa.

**Local permanente** tem `source`, `source_external_id`, `canonical_name`, `poi_type`, `lat`, `lng` e `source_url`. Incluir endereço, cidade e UF quando conhecidos. O local entra como candidato inativo. Horários de ocorrência pertencem aos eventos. O cadastro de um aeroporto, arena ou rodoviária identifica um local relevante. O cálculo de alta incidência permanece no backend e depende de observações elegíveis.

**Lotes e reenvio.** Usar `dry_run: true` no primeiro teste. Gerar um `run_id` distinto por lote de eventos ou lugares e outro para o envio que grava. Ao repetir uma tentativa de envio, conservar o mesmo ID e corpo. Se o conteúdo mudar, gerar um novo ID. Ler `items` e `rejected` mesmo com HTTP 200. Respeitar `Retry-After` em HTTP 429 e guardar o recibo se a auditoria HTTP vier inconclusiva. O V2 prevê 2 MB por corpo, até 50 lugares e limite de eventos por lote informado no ping, com padrão documentado de 200.

**Identidade e duplicidade.** Atualizar eventos pela combinação `source + external_id` e locais por `source + source_external_id`. Sinalizar possíveis duplicatas entre fontes ou entre coleta e cadastro manual para decisão humana. Uma proposta de outra origem não assume a propriedade de um registro canônico. Preservar as decisões anteriores de revisão conforme o V2.

## 6. Como ver os dados e o que falta no Admin

| O que conferir | Caminho |
| --- | --- |
| Lote enviado | `/admin/radar` → **Envios**. Para o Dell, filtrar por coletor e localizar o `run_id`. Para o JSON, disponibilizar a consulta pelo `batch_id` com o recibo e o resultado por item. |
| Eventos candidatos | **Recebidos**. Conferir origem, horário, mapa, estado de revisão e histórico antes de aprovar. |
| Locais candidatos | **Lugares**. Conferir nome, categoria, mapa, evidência e revisão. A consulta administrativa atual lista candidatos inativos. |
| Resultado para motorista | Usar uma conta de teste com acesso ao Radar. Na vc114, conferir um evento em **Eventos em geral** com localização de teste e horário elegíveis. Conferir um local pela busca ou pelo Radar contextual, com destino e ETA válidos, conforme o build homologado. |

O contrato reaproveita as rotas autenticadas de consulta e revisão do Admin para eventos e lugares. A instância deve completar **upload e prévia do JSON, importação seletiva em lote, pesquisa de ativos e inativos, revisão em lote, recibo administrativo e formulário de endereço avulso** na mesma interface. Reaproveitar serviços, validação e auditoria existentes. O servidor deve identificar o operador pela sessão e preservar a fonte original e o método de entrada de cada registro. A chave do Dell atende ao fluxo automatizado V2. O upload administrativo usa a sessão do operador.

Para a consulta do motorista, já existem `GET /api/v1/radar/events`, `GET /api/v1/radar/poi/search` e `GET /api/v1/radar/contextual`, com autenticação do app e acesso correspondente. Manter essas rotas e o contrato externo V2 como pontos de integração. A coleta usa os dados do Radar sem acesso direto ao banco.

## 7. Entrega pedida à instância desenvolvedora

1. Usar o repositório do coletor para revisar o código, o esquema e os exemplos. Rodar os testes locais sem chave. Para o piloto real, confirmar a URL da API e provisionar uma chave individual para o Dell com fontes, escopos, limites e validade.
2. Informar a fonte autorizada do piloto. Entregar dois exemplos validados de requisição e resposta, um de evento e um de local. Confirmar as telas ou rotas usadas para acompanhar cada candidato.
3. Implementar **Importar JSON** com o esquema fornecido neste pacote. Usar o exemplo de homologação para verificar a prévia, o recebimento seletivo em lote, o recibo, o reenvio idempotente e a aprovação em lote. Homologar também **Adicionar endereço** com um local confirmado em mapa e evidência em nota. Testar a prévia de um arquivo v1 e de um v2, os três ícones de locais, a capa aprovada e a indisponível. O mesmo evento deve continuar importável e consultável com seu ícone quando a imagem falhar.
4. Conferir ping, simulação e reenvio com o mesmo `run_id` no teste local. Quando houver autorização para um piloto na API real, usar um evento e um local reais e autorizados, repetir a tentativa com o mesmo `run_id` e conferir a revisão no Admin. Confirmar que um candidato pendente fica fora das consultas do app e que o aprovado aparece sob as condições de localização e horário do teste. Confirmar também que a chave do Dell é recusada nas rotas administrativas.
5. Retornar o ambiente, o commit, os IDs dos lotes de teste, o caminho usado no app e as pendências. Só então ativar a rotina de coleta do piloto.

## Referências verificadas

- [Validação de upload de arquivos — OWASP](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [Validação de buscas externas no servidor — OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)

- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation)

- [Robots.txt do SP Mais Cultura](https://spmaiscultura.prefeitura.sp.gov.br/robots.txt) · [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html#section-1)
