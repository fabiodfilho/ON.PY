import base64
from io import BytesIO
import json
import re
import time

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class CanvasAuditoriaService:
    def __init__(self, api_token: str, canvas_domain: str = "unifacisa.instructure.com"):
        self.api_token = api_token
        self.canvas_domain = canvas_domain
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_token}"})

        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def _emit(self, event_type: str, message: str, **extra) -> str:
        payload = {"type": event_type, "message": message, **extra}
        return json.dumps(payload, ensure_ascii=False) + "\n"

    def _fetch_all_pages(self, url: str, params=None):
        results = []
        response = self.session.get(url, params=params, timeout=30)

        while response.status_code == 200:
            results.extend(response.json())
            if "next" in response.links:
                next_url = response.links["next"]["url"]
                time.sleep(0.2)
                response = self.session.get(next_url, timeout=30)
            else:
                break

        return results, response.status_code

    def _get_subaccount_name(self, subconta_id: str) -> str:
        url = f"https://{self.canvas_domain}/api/v1/accounts/{subconta_id}"
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                nome_sujo = response.json().get("name", f"Subconta {subconta_id}")
                caracteres_invalidos = r"[]:*?/\'"
                nome_limpo = "".join(
                    c for c in nome_sujo if c not in caracteres_invalidos
                )
                return nome_limpo[:31]
        except Exception:
            pass
        return f"Subconta {subconta_id}"

    def auditar_cursos_stream(self, subcontas_raw: str):
        subcontas_ids = [
            s.strip() for s in re.split(r"[,\n\r;\s]+", subcontas_raw) if s.strip()
        ]

        if not subcontas_ids:
            yield self._emit("error", "Nenhuma subconta válida foi informada.")
            return

        yield self._emit("log", "Configurando sessão segura com o Canvas...")

        wb = Workbook()
        wb.remove(wb.active)
        teve_dados = False
        total_erros_geral = 0

        for subconta_id in subcontas_ids:
            nome_aba = self._get_subaccount_name(subconta_id)
            yield self._emit(
                "log", f"▶ INICIANDO AUDITORIA: Subconta {subconta_id} ({nome_aba})"
            )

            courses_url = (
                f"https://{self.canvas_domain}/api/v1/accounts/{subconta_id}/courses"
            )
            courses_params = {
                "state[]": "available",
                "include_subaccounts": True,
                "per_page": 100,
            }

            cursos, status_code = self._fetch_all_pages(courses_url, courses_params)

            if status_code == 401:
                yield self._emit(
                    "error", "Token de API inválido ou sem permissão de acesso."
                )
                return

            if status_code != 200:
                yield self._emit(
                    "error",
                    f"Erro ao acessar subconta {subconta_id}: Status HTTP {status_code}",
                )
                continue

            yield self._emit(
                "log", f"✅ {len(cursos)} cursos ativos encontrados na subconta {subconta_id}."
            )

            if not cursos:
                yield self._emit(
                    "log", f"Aviso: Nenhum curso ativo na subconta {subconta_id}."
                )
                continue

            relatorio = []
            codigos_da_subconta = set()
            erros_subconta = 0

            for index, curso in enumerate(cursos, start=1):
                course_id = curso["id"]
                course_name = curso.get("name", f"Curso sem nome ({course_id})")

                if index == 1 or index % 10 == 0 or index == len(cursos):
                    yield self._emit(
                        "log",
                        f"   Auditando curso {index}/{len(cursos)}: {course_id}...",
                    )

                match_codigo = re.match(r"^(\d+)", course_name.strip())
                if match_codigo:
                    codigos_da_subconta.add(match_codigo.group(1))

                groups_url = (
                    f"https://{self.canvas_domain}/api/v1/courses/"
                    f"{course_id}/assignment_groups"
                )
                grupos, _ = self._fetch_all_pages(
                    groups_url, {"include[]": "assignments", "per_page": 100}
                )

                for grupo in grupos:
                    nome_grupo = grupo["name"]
                    grupo_oficial = grupo.get("sis_source_id") is not None
                    tarefas = grupo.get("assignments", [])

                    for tarefa in tarefas:
                        if not tarefa.get("published", False):
                            continue

                        nome_tarefa = tarefa["name"]
                        pontos_raw = tarefa.get("points_possible")
                        pontos = float(pontos_raw) if pontos_raw is not None else 0.0
                        pendentes = tarefa.get("needs_grading_count", 0)

                        erro_caixinha = "OK"
                        if pontos > 0 and not grupo_oficial:
                            erro_caixinha = "Erro: Grupo não oficial"
                            erros_subconta += 1
                            total_erros_geral += 1

                        relatorio.append(
                            {
                                "ID do Curso": course_id,
                                "Nome do Curso": course_name,
                                "Nome da Caixinha": nome_grupo,
                                "Nome da Tarefa": nome_tarefa,
                                "Notas Pendentes": pendentes,
                                "Status da Caixinha": erro_caixinha,
                            }
                        )

            yield self._emit(
                "log",
                f"Subconta {subconta_id} finalizada: {len(relatorio)} tarefas analisadas ({erros_subconta} erros de caixinha).",
            )

            if relatorio:
                teve_dados = True
                ws = wb.create_sheet(title=nome_aba)

                colunas = list(relatorio[0].keys())
                ws.append(colunas)

                fonte_cabecalho = Font(bold=True, color="FFFFFF")
                fundo_cabecalho = PatternFill(
                    start_color="1F497D", end_color="1F497D", fill_type="solid"
                )
                alinhamento_centro = Alignment(horizontal="center", vertical="center")

                for celula in ws[1]:
                    celula.font = fonte_cabecalho
                    celula.fill = fundo_cabecalho
                    celula.alignment = alinhamento_centro

                for linha in relatorio:
                    ws.append(
                        [
                            linha["ID do Curso"],
                            linha["Nome do Curso"],
                            linha["Nome da Caixinha"],
                            linha["Nome da Tarefa"],
                            linha["Notas Pendentes"],
                            linha["Status da Caixinha"],
                        ]
                    )

                ws.column_dimensions["A"].width = 15
                ws.column_dimensions["B"].width = 45
                ws.column_dimensions["C"].width = 30
                ws.column_dimensions["D"].width = 45
                ws.column_dimensions["E"].width = 20
                ws.column_dimensions["F"].width = 30

                if codigos_da_subconta:
                    string_codigos = ",".join(sorted(list(codigos_da_subconta)))
                    ws.append([])
                    ws.append(["CÓDIGOS DOS CURSOS:", string_codigos])

                    linha_final = ws.max_row
                    ws.cell(row=linha_final, column=1).font = Font(bold=True)
                    ws.cell(row=linha_final, column=2).font = Font(bold=True)

        if teve_dados:
            buffer = BytesIO()
            wb.save(buffer)
            report_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
            yield self._emit(
                "success",
                f"Auditoria concluída! {total_erros_geral} divergência(s) encontrada(s). Baixando planilha...",
                report_base64=report_b64,
                filename="auditoria_unifacisa_multicontas.xlsx",
            )
        else:
            yield self._emit(
                "success",
                "Auditoria concluída! Nenhuma tarefa publicada foi encontrada nas subcontas informadas.",
            )