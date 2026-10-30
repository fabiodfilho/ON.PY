import re

from flask import (
    Blueprint,
    Response,
    jsonify,
    render_template,
    request,
    stream_with_context,
)

from Model.ofertas_engine import executar_extracao_ofertas
from Model.services.canvas_periodos_service import CanvasPeriodosService
from Model.services.canvas_inativar_service import CanvasInativarService

shortcut_periodos_bp = Blueprint("shortcut_periodos", __name__)
shortcut_inativar_bp = Blueprint("shortcut_inativar", __name__)


@shortcut_periodos_bp.route("/shortcuts/periodos", methods=["GET"])
def render_periodos_view():
    """Renderiza a view principal do atalho de períodos."""
    return render_template("shortcut-periodos.html")


@shortcut_periodos_bp.route("/api/shortcuts/periodos/execute", methods=["POST"])
def execute_periodos_update():
    """Processa a atualização em lote dos períodos com streaming em tempo real."""
    payload = request.get_json() or {}

    api_token = payload.get("api_token", "").strip()
    term_id = payload.get("term_id", "").strip()
    alvos = payload.get("alvos", "").strip()
    target_type = payload.get("target_type", "subaccounts").strip()
    start_at = payload.get("start_at")
    end_at = payload.get("end_at")

    if not api_token or not term_id or not alvos:
        return jsonify({"error": "Preencha todos os campos obrigatórios."}), 400

    service = CanvasPeriodosService(api_token=api_token)

    stream_generator = service.atualizar_periodos_em_lote_stream(
        term_id=term_id,
        alvos_raw=alvos,
        target_type=target_type,
        start_at=start_at,
        end_at=end_at,
    )

    return Response(stream_with_context(stream_generator), mimetype="application/x-ndjson")


def init_routes(app):
    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/sispy")
    def sispy_page():
        return render_template("index.old.html")


def init_ofertas_routes(app):
    @app.route("/shortcuts/ofertas")
    def page_shortcut_ofertas():
        return render_template("shortcut-ofertas.html")

    @app.route("/api/shortcuts/ofertas/executar", methods=["POST"])
    def api_executar_ofertas():
        api_token = request.form.get("api_token", "").strip()
        subcontas_raw = request.form.get("subcontas", "").strip()

        if not api_token:
            return Response(
                "ERROR: O Token de API do Canvas é obrigatório.\n",
                mimetype="text/plain",
            )

        subcontas_ids = [
            subconta.strip()
            for subconta in re.split(r"[,\n\r]+", subcontas_raw)
            if subconta.strip()
        ]
        if not subcontas_ids:
            return Response(
                "ERROR: Nenhuma subconta válida informada.\n",
                mimetype="text/plain",
            )

        logs = executar_extracao_ofertas(
            api_token,
            subcontas_ids,
        )
        return Response(stream_with_context(logs), mimetype="text/plain")


@shortcut_inativar_bp.route("/shortcuts/inativar", methods=["GET"])
def render_inativar_view():
    """Renderiza a view principal do atalho de inativação."""
    return render_template("shortcut-inativar.html")


@shortcut_inativar_bp.route("/api/shortcuts/inativar/execute", methods=["POST"])
def execute_inativar_update():
    """Processa a inativação e despublicação com streaming NDJSON."""
    payload = request.get_json() or {}

    api_token = payload.get("api_token", "").strip()
    alvos = payload.get("alvos", "").strip()

    if not api_token or not alvos:
        return jsonify({"error": "Preencha todos os campos obrigatórios."}), 400

    service = CanvasInativarService(api_token=api_token)
    stream_generator = service.inativar_e_despublicar_stream(alvos_raw=alvos)

    return Response(
        stream_with_context(stream_generator),
        mimetype="application/x-ndjson",
    )