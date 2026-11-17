# on.py

Aplicação web em Flask para automatizar operações de integração e administração
do Canvas LMS. O projeto reúne duas áreas:

- **sis.py**: gera arquivos CSV no formato de importação SIS do Canvas.
- **shortcuts.py**: executa automações em lote no Canvas e exibe os logs em
  tempo real.

## Funcionalidades

### sis.py

Disponível em `/sis`:

- gera `matriculas_sis.csv` com as colunas `course_id`, `user_id`, `role` e
  `status`;
- aceita vários blocos de cursos e usuários;
- permite selecionar os papéis **Aluno**, **Professor** ou **Coordenador**;
- gera uma linha para cada combinação de curso e usuário;
- envia o arquivo diretamente para download, pronto para a importação SIS do
  Canvas.

Os IDs dos cursos são informados diretamente. A versão atual não depende da
planilha `Model/BD-OFERTAS-261.1.xlsx` para gerar o CSV.

### shortcuts.py

Disponível em `/shortcuts`, com as seguintes automações:

- **Extração de Ofertas** (`/shortcuts/codigos-ofertas`): consulta cursos
  ativos e despublicados por subconta e gera um relatório Excel com os códigos
  encontrados.
- **Atualização de Períodos Letivos** (`/shortcuts/periodos`): altera em lote
  o período letivo e, opcionalmente, as datas de início e fim de cursos
  selecionados por subconta ou código.
- **Inativar e Despublicar** (`/shortcuts/inativar`): inativa as matrículas
  dos cursos informados e despublica os cursos.
- **Auditoria** (`/shortcuts/auditoria`): analisa tarefas publicadas, grupos de
  tarefas e notas pendentes, gerando um relatório Excel por subconta.

As automações do Canvas recebem o token de API apenas durante a execução,
consultam o domínio `unifacisa.instructure.com` e transmitem o progresso em
streaming. O token não deve ser salvo no código, em arquivos do projeto ou em
commits.

## Requisitos

- Python 3.10 ou superior;
- pip;
- acesso à API do Canvas para usar os atalhos;
- Docker e Docker Compose, caso a execução seja feita em contêiner.

## Execução local

No Windows, PowerShell ou em outro terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Depois, acesse <http://127.0.0.1:5000>.

Para executar com o servidor de produção incluído no projeto:

```powershell
gunicorn --workers 3 --bind 0.0.0.0:8000 main:app
```

> O `main.py` inicia o Flask em modo de desenvolvimento (`debug=True`). Use
> Gunicorn ou outro servidor WSGI em produção.

## Execução com Docker

```powershell
docker compose up --build
```

A aplicação ficará disponível em <http://127.0.0.1:8000>. Para encerrar:

```powershell
docker compose down
```

O contêiner usa Python 3.10, instala as dependências de
`requirements.txt` e inicia a aplicação com Gunicorn.

## Rotas principais

| Rota | Método | Descrição |
| --- | --- | --- |
| `/` | GET | Página inicial do on.py |
| `/sis` | GET | Interface de geração do CSV SIS |
| `/gerar-csv` | POST | Gera e baixa o CSV SIS |
| `/shortcuts` | GET | Lista de automações |
| `/shortcuts/codigos-ofertas` | GET | Interface de extração de ofertas |
| `/shortcuts/periodos` | GET | Interface de atualização de períodos |
| `/shortcuts/inativar` | GET | Interface de inativação e despublicação |
| `/shortcuts/auditoria` | GET | Interface de auditoria |

As APIs de execução dos atalhos são:

- `POST /api/shortcuts/ofertas/executar` — formulário com `api_token` e
  `subcontas`;
- `POST /api/shortcuts/periodos/execute` — JSON com `api_token`, `term_id`,
  `alvos`, `target_type` e datas opcionais;
- `POST /api/shortcuts/inativar/execute` — JSON com `api_token` e `alvos`;
- `POST /api/shortcuts/auditoria/execute` — JSON com `api_token` e
  `subcontas`.

As respostas dos atalhos são transmitidas como texto ou NDJSON, conforme a
funcionalidade, para que a interface possa mostrar os logs durante a execução.

## Estrutura do projeto

```text
SISPY/
├── main.py                         # Criação da aplicação e rotas de páginas
├── requirements.txt                # Dependências Python
├── Dockerfile                      # Imagem de produção
├── docker-compose.yml              # Execução local via Docker Compose
├── Controller/
│   ├── views.py                    # Rotas das páginas e APIs
│   └── csv_controller.py           # Geração do CSV SIS
├── Model/
│   ├── ofertas_engine.py           # Extração de ofertas do Canvas
│   └── services/
│       ├── canvas_periodos_service.py
│       ├── canvas_inativar_service.py
│       └── canvas_auditoria_service.py
└── View/
    ├── templates/                  # Interfaces HTML
    └── static/                     # CSS, JavaScript e imagens
```

## Dependências

- **Flask**: servidor web e roteamento;
- **Gunicorn**: servidor WSGI para produção;
- **Requests**: comunicação com a API do Canvas;
- **Pandas** e **OpenPyXL**: leitura e geração de planilhas Excel.

Instale todas com:

```powershell
python -m pip install -r requirements.txt
```

## Observações operacionais

- Use um token do Canvas com as permissões necessárias para cada automação.
- Confirme os IDs de cursos, subcontas e períodos antes de executar operações
  em lote.
- As ações de inativação e despublicação alteram dados no Canvas e devem ser
  executadas somente após a conferência dos alvos.
- A aplicação usa o domínio padrão da Unifacisa definido nos serviços. Para
  apontar para outro ambiente Canvas, ajuste a configuração dos serviços antes
  da implantação.

## Contribuição

1. Crie uma branch para a alteração.
2. Faça mudanças focadas e atualize a documentação relacionada.
3. Valide a execução local ou via Docker.
4. Abra um Pull Request descrevendo o comportamento alterado.
