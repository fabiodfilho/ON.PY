import os
import re

from flask import (
    Response,
    render_template,
    request,
    send_from_directory,
    stream_with_context,
)

from Model.ofertas_engine import executar_extracao_ofertas


def init_routes(app):
    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/sispy")
    def sispy_page():
        return render_template("index.old.html")


def init_ofertas_routes(app):
    temp_reports_dir = os.path.join(app.root_path, "temp_reports")
    os.makedirs(temp_reports_dir, exist_ok=True)

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
            temp_reports_dir,
        )
        return Response(stream_with_context(logs), mimetype="text/plain")

    @app.route("/api/shortcuts/ofertas/download/<filename>")
    def download_ofertas_report(filename):
        return send_from_directory(
            temp_reports_dir,
            filename,
            as_attachment=True,
        )
