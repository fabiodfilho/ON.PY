import json
import re
from typing import Optional, Tuple
import requests


class CanvasPeriodosService:
    MAX_PAGES = 50

    def __init__(
        self,
        api_token: str,
        base_url: str = "https://unifacisa.instructure.com",
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Authorization": "Bearer " + api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _parse_ids(self, raw_input: str) -> list:
        return [item.strip() for item in re.split(r"[\n,]+", raw_input) if item.strip()]

    @staticmethod
    def _next_page_url(link_header: str) -> Optional[str]:
        if not link_header:
            return None
        for link in link_header.split(","):
            match = re.match(r"\s*<([^>]+)>;\s*rel=\"next\"", link)
            if match:
                return match.group(1)
        return None

    def _safe_request(self, method: str, url: str, **kwargs) -> requests.Response:
        res = requests.request(method, url, headers=self.headers, timeout=15, **kwargs)
        content_type = res.headers.get("Content-Type", "")
        if "application/json" not in content_type and res.status_code >= 400:
            raise ValueError(
                f"HTTP {res.status_code}: O Canvas não retornou JSON. Verifique se o token tem acesso ao ambiente."
            )
        return res

    def _resolve_canvas_term_id(self, term_input: str) -> Tuple[str, str]:
        term_str = str(term_input).strip()
        url = f"{self.base_url}/api/v1/accounts/self/terms"
        params = {"per_page": 100}

        while url:
            try:
                res = self._safe_request("GET", url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    terms = data.get("enrollment_terms", []) if isinstance(data, dict) else []
                    for t in terms:
                        t_id = str(t.get("id", ""))
                        t_sis = str(t.get("sis_term_id", "")).strip()
                        t_name = t.get("name", "")

                        if t_sis == term_str:
                            return t_id, f"'{t_name}' (ID Canvas: {t_id} | SIS ID: {t_sis})"
                        if t_id == term_str:
                            return t_id, f"'{t_name}' (ID Canvas: {t_id})"

                    url = self._next_page_url(res.headers.get("Link", ""))
                    params = {}
                else:
                    break
            except Exception:
                break

        return f"sis_term_id:{term_str}", f"SIS ID '{term_str}' (via sis_term_id:)"

    def _list_courses(self, account_id: str, search_term: Optional[str] = None) -> list:
        courses = []
        url = f"{self.base_url}/api/v1/accounts/{account_id}/courses"
        params = {"include[]": "subaccount", "state[]": "all", "per_page": 100}
        if search_term:
            params["search_term"] = search_term

        page = 0
        while url and page < self.MAX_PAGES:
            page += 1
            res = self._safe_request("GET", url, params=params)
            res.raise_for_status()
            data = res.json()
            if isinstance(data, list):
                courses.extend(data)
            url = self._next_page_url(res.headers.get("Link", ""))
            params = {}
        return courses

    def atualizar_periodos_em_lote_stream(
        self,
        term_id: str,
        alvos_raw: str,
        target_type: str = "subaccounts",
        start_at: Optional[str] = None,
        end_at: Optional[str] = None,
    ):
        targets = self._parse_ids(alvos_raw)

        yield json.dumps({"type": "info", "message": f"Conectado ao Canvas Beta ({self.base_url})..."}) + "\n"

        canvas_term_id, term_display = self._resolve_canvas_term_id(term_id)
        yield json.dumps({"type": "info", "message": f"Período mapeado: {term_display}"}) + "\n"

        courses = []
        if target_type == "course_codes":
            yield json.dumps({"type": "info", "message": f"Buscando {len(targets)} código(s) de curso na conta raiz."}) + "\n"
            for code in targets:
                try:
                    found = self._list_courses("self", search_term=code)
                    matched = [c for c in found if re.match(rf"^{re.escape(code)}(?:\D|$)", c.get("name", ""))]
                    courses.extend(matched)
                except Exception as e:
                    yield json.dumps({"type": "error", "message": f"Erro ao buscar curso {code}: {e}"}) + "\n"
        else:
            yield json.dumps({"type": "info", "message": f"Listando disciplinas de {len(targets)} subconta(s)..."}) + "\n"
            for account_id in targets:
                try:
                    sub_courses = self._list_courses(account_id)
                    courses.extend(sub_courses)
                    yield json.dumps({"type": "info", "message": f"Subconta {account_id}: {len(sub_courses)} curso(s) encontrado(s)."}) + "\n"
                except Exception as e:
                    yield json.dumps({"type": "error", "message": f"Erro na subconta {account_id}: {e}"}) + "\n"

        unique_courses = {str(c.get("id")): c for c in courses if c.get("id")}
        yield json.dumps({"type": "info", "message": f"Total de {len(unique_courses)} curso(s) único(s) para atualizar."}) + "\n"

        for course_id, course in unique_courses.items():
            course_name = course.get("name", "Sem Nome")
            
            # Payload configurado para alterar o período e forçar a participação para 'Período'
            payload = {
                "course": {
                    "enrollment_term_id": canvas_term_id,
                    "restrict_enrollments_to_course_dates": False,
                }
            }
            if start_at:
                payload["course"]["start_at"] = f"{start_at}T00:00:00Z"
            if end_at:
                payload["course"]["end_at"] = f"{end_at}T23:59:59Z"

            try:
                res = requests.put(
                    f"{self.base_url}/api/v1/courses/{course_id}",
                    json=payload,
                    headers=self.headers,
                    timeout=15,
                )
                if res.status_code == 200:
                    msg = f"Curso ID {course_id} ('{course_name}') -> Período e Participação atualizados!"
                    yield json.dumps({"type": "success", "message": msg}) + "\n"
                else:
                    detail = res.json().get("errors", res.text) if "json" in res.headers.get("Content-Type", "") else f"HTTP {res.status_code}"
                    msg = f"Falha no curso ID {course_id}: {detail}"
                    yield json.dumps({"type": "error", "message": msg}) + "\n"
            except Exception as e:
                msg = f"Erro de conexão no curso ID {course_id}: {e}"
                yield json.dumps({"type": "error", "message": msg}) + "\n"

        yield json.dumps({"type": "done"}) + "\n"