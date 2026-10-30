import os
import re
import time
import uuid

import requests
from openpyxl import Workbook
from openpyxl.styles import Font
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def executar_extracao_ofertas(
    api_token,
    subcontas_ids,
    temp_reports_dir,
    canvas_domain="unifacisa.instructure.com",
):
    session = requests.Session()
    session.headers.update({"Authorization": "Bearer " + api_token})
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    def fetch_all_pages(url, params=None):
        results = []
        response = session.get(url, params=params, timeout=30)
        while response.status_code == 200:
            results.extend(response.json())
            if "next" not in response.links:
                break
            time.sleep(0.2)
            response = session.get(response.links["next"]["url"], timeout=30)
        return results, response.status_code

    def get_subaccount_name(subconta_id):
        url = f"https://{canvas_domain}/api/v1/accounts/{subconta_id}"
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                nome_sujo = response.json().get(
                    "name", f"Subconta {subconta_id}"
                )
                nome_limpo = "".join(
                    caractere
                    for caractere in nome_sujo
                    if caractere not in r"[]:*?/\'"
                )
                return nome_limpo[:31]
        except (requests.RequestException, ValueError):
            pass
        return f"Subconta {subconta_id}"

    yield "LOG: Configurando sessão segura com o Canvas...\n"

    workbook = Workbook()
    workbook.remove(workbook.active)
    teve_dados = False

    for subconta_id in subcontas_ids:
        nome_aba = get_subaccount_name(subconta_id)
        yield (
            f"LOG: Coletando subconta {subconta_id} "
            f"({nome_aba})...\n"
        )

        courses_url = (
            f"https://{canvas_domain}/api/v1/accounts/"
            f"{subconta_id}/courses"
        )
        cursos, status = fetch_all_pages(
            courses_url,
            {
                "state[]": "all",
                "include_subaccounts": True,
                "per_page": 100,
            },
        )

        if status == 401:
            yield (
                "ERROR: Token de API inválido ou sem permissão "
                "de acesso.\n"
            )
            return

        codigos_por_estado = {"ativos": set(), "despublicados": set()}
        for curso in cursos:
            estado = {
                "available": "ativos",
                "unpublished": "despublicados",
            }.get(curso.get("workflow_state"))
            if not estado:
                continue

            match_codigo = re.match(r"^(\d+)", curso.get("name", "").strip())
            if match_codigo:
                codigos_por_estado[estado].add(match_codigo.group(1))

        num_ativos = len(codigos_por_estado["ativos"])
        num_despublicados = len(codigos_por_estado["despublicados"])
        yield (
            f"LOG: Subconta {subconta_id} -> {num_ativos} ativos, "
            f"{num_despublicados} despublicados com códigos numéricos.\n"
        )

        if not any(codigos_por_estado.values()):
            continue

        teve_dados = True
        worksheet = workbook.create_sheet(title=nome_aba)
        worksheet.append(["SITUAÇÃO", "CÓDIGOS"])
        worksheet.append(
            ["ATIVOS", ",".join(sorted(codigos_por_estado["ativos"]))]
        )
        worksheet.append(
            [
                "DESPUBLICADOS",
                ",".join(sorted(codigos_por_estado["despublicados"])),
            ]
        )

        for cell in worksheet[1]:
            cell.font = Font(bold=True)
        worksheet.column_dimensions["A"].width = 25
        worksheet.column_dimensions["B"].width = 120

    if teve_dados:
        filename = f"ofertas_canvas_{uuid.uuid4().hex[:8]}.xlsx"
        filepath = os.path.join(temp_reports_dir, filename)
        workbook.save(filepath)
        yield "SUCCESS: Coleta concluída com sucesso! Relatório Excel gerado.\n"
        yield f"DOWNLOAD:{filename}\n"
    else:
        yield (
            "LOG: Processo concluído. Nenhum código numérico foi "
            "encontrado nas subcontas informadas.\n"
        )
