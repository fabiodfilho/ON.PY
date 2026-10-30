import json
import re
import time
from typing import Optional
import requests


class CanvasInativarService:
    MAX_PAGES = 50

    def __init__(
        self,
        api_token: str,
        base_url: str = "https://unifacisa.instructure.com",
    ):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_token}",
                "Authorization": "Bearer " + api_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _parse_ids(self, raw_input: str) -> list:
        return [
            item.strip()
            for item in re.split(r"[\n,]+", raw_input)
            if item.strip()
        ]

    @staticmethod
    def _next_page_url(link_header: str) -> Optional[str]:
        if not link_header:
            return None
        for link in link_header.split(","):
            match = re.match(r"\s*<([^>]+)>;\s*rel=\"next\"", link)
            if match:
                return match.group(1)
        return None

    def _list_courses(self, search_term: str) -> list:
        courses = []
        url = f"{self.base_url}/api/v1/accounts/self/courses"
        params = {
            "include[]": "subaccount",
            "state[]": "all",
            "per_page": 100,
            "search_term": search_term,
        }

        page = 0
        while url and page < self.MAX_PAGES:
            page += 1
            res = self.session.get(url, params=params, timeout=15)
            res.raise_for_status()
            data = res.json()
            if isinstance(data, list):
                courses.extend(data)
            url = self._next_page_url(res.headers.get("Link", ""))
            params = None

        return courses

    def _course_id_exists(self, course_id: str) -> bool:
        response = self.session.get(
            f"{self.base_url}/api/v1/courses/{course_id}",
            timeout=15,
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    def _resolve_course_ids(self, targets: list) -> tuple[list, list]:
        course_ids = []
        errors = []

        for target in targets:
            if target.isdigit() and len(target) != 6:
                course_ids.append(target)
                continue
            if len(target) != 6 or not target.isalnum():
                errors.append(
                    f"Entrada inválida '{target}': informe um ID numérico ou código alfanumérico de 6 caracteres."
                )
                continue

            try:
                if self._course_id_exists(target):
                    course_ids.append(target)
                    continue

                courses = self._list_courses(target)
                matched = [
                    course
                    for course in courses
                    if re.match(
                        rf"^{re.escape(target)}(?:\D|$)",
                        str(course.get("name", "")),
                    )
                    and course.get("id")
                ]
                if matched:
                    course_ids.extend(str(course["id"]) for course in matched)
                else:
                    course_ids.append(target)
            except Exception as exc:
                errors.append(f"Erro ao buscar o código {target}: {exc}")
                course_ids.append(target)

        unique_ids = list(dict.fromkeys(course_ids))
        return unique_ids, errors

    def inativar_e_despublicar_stream(self, alvos_raw: str):
        targets = self._parse_ids(alvos_raw)
        if not targets:
            yield json.dumps(
                {
                    "type": "error",
                    "message": "Nenhum ID ou código válido foi informado.",
                }
            ) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
            return

        course_ids, resolution_errors = self._resolve_course_ids(targets)

        yield json.dumps(
            {
                "type": "info",
                "message": f"Iniciando processo para {len(course_ids)} curso(s)...",
            }
        ) + "\n"

        for error in resolution_errors:
            yield json.dumps({"type": "error", "message": error}) + "\n"

        for course_id in course_ids:
            yield json.dumps(
                {
                    "type": "info",
                    "message": f"----------------------------------------",
                }
            ) + "\n"
            yield json.dumps(
                {
                    "type": "info",
                    "message": f"Buscando matrículas do curso ID {course_id}...",
                }
            ) + "\n"

            # 1. Buscar matrículas
            url_busca = f"{self.base_url}/api/v1/courses/{course_id}/enrollments"
            params = {"per_page": 100}
            matriculas = []

            try:
                while url_busca:
                    res = self.session.get(url_busca, params=params, timeout=15)
                    if res.status_code != 200:
                        yield json.dumps(
                            {
                                "type": "error",
                                "message": f"Falha ao buscar curso {course_id}: HTTP {res.status_code}",
                            }
                        ) + "\n"
                        break

                    dados = res.json()
                    matriculas.extend(dados)

                    # Paginação
                    links = res.links
                    if "next" in links:
                        url_busca = links["next"]["url"]
                        params = None
                    else:
                        url_busca = None

            except Exception as e:
                yield json.dumps(
                    {
                        "type": "error",
                        "message": f"Erro de conexão no curso {course_id}: {e}",
                    }
                ) + "\n"
                continue

            yield json.dumps(
                {
                    "type": "info",
                    "message": f"Curso {course_id}: {len(matriculas)} matrícula(s) localizada(s).",
                }
            ) + "\n"

            sucessos = 0
            falhas = 0

            # 2. Inativar cada matrícula
            for mat in matriculas:
                enrollment_id = mat.get("id")
                nome_user = mat.get("user", {}).get("name", "Usuário Desconhecido")
                role = mat.get("role", "Papel")

                if mat.get("enrollment_state") == "inactive":
                    yield json.dumps(
                        {
                            "type": "info",
                            "message": f"• '{nome_user}' já está inativo. Pulando...",
                        }
                    ) + "\n"
                    continue

                inativar_url = f"{self.base_url}/api/v1/courses/{course_id}/enrollments/{enrollment_id}"
                try:
                    del_res = self.session.delete(
                        inativar_url, params={"task": "inactivate"}, timeout=15
                    )
                    if del_res.status_code == 200:
                        sucessos += 1
                        yield json.dumps(
                            {
                                "type": "success",
                                "message": f"• {nome_user} ({role}) -> Inativado(a) com sucesso.",
                            }
                        ) + "\n"
                    else:
                        falhas += 1
                        yield json.dumps(
                            {
                                "type": "error",
                                "message": f"• Falha ao inativar {nome_user}: HTTP {del_res.status_code}",
                            }
                        ) + "\n"
                except Exception as e:
                    falhas += 1
                    yield json.dumps(
                        {
                            "type": "error",
                            "message": f"• Erro na inativação de {nome_user}: {e}",
                        }
                    ) + "\n"

                time.sleep(0.05)

            # 3. Despublicar o curso
            yield json.dumps(
                {
                    "type": "info",
                    "message": f"Despublicando o curso {course_id}...",
                }
            ) + "\n"
            despublicar_url = f"{self.base_url}/api/v1/courses/{course_id}"

            try:
                upd_res = self.session.put(
                    despublicar_url,
                    json={"course": {"event": "claim"}},
                    timeout=15,
                )
                if upd_res.status_code == 200:
                    yield json.dumps(
                        {
                            "type": "success",
                            "message": f"Curso {course_id} despublicado com sucesso!",
                        }
                    ) + "\n"
                else:
                    try:
                        detail = upd_res.json().get("errors", upd_res.text)
                    except ValueError:
                        detail = upd_res.text
                    yield json.dumps(
                        {
                            "type": "error",
                            "message": f"Erro ao despublicar curso {course_id}: HTTP {upd_res.status_code} - {detail}",
                        }
                    ) + "\n"
            except Exception as e:
                yield json.dumps(
                    {
                        "type": "error",
                        "message": f"Erro na despublicação do curso {course_id}: {e}",
                    }
                ) + "\n"

        yield json.dumps({"type": "done"}) + "\n"