from flask import Flask, render_template, request, Response, jsonify
from Controller.csv_controller import processar_geracao_csv
from Controller.views import init_ofertas_routes, shortcut_periodos_bp, shortcut_inativar_bp

app = Flask(__name__, 
            template_folder='View/templates', 
            static_folder='View/static')

@app.route('/')
def index():
    return render_template('home.html')

@app.route("/shortcuts")
def shortcuts_page():
    return render_template("shortcuts.html")

@app.route("/shortcuts/codigos-ofertas")
def shortcuts_codigos_ofertas_page():
    return render_template("shortcut-ofertas.html")

@app.route('/sis')
def sis_page():
    return render_template('sis.html')

@app.route('/home.old')
def home_old():
    return render_template('index.old.html')

@app.route('/shortcuts/inativar')
def inativar_page():
    return render_template('shortcut-inativar.html')

@app.route('/sispy')
def sispy_page():
    return render_template('sis.html')

@app.route('/gerar-csv', methods=['POST'])
def gerar_csv():
    lista_cursos = request.form.getlist('cursos[]')
    lista_matriculas = request.form.getlist('matriculas[]')
    lista_tipos = request.form.getlist('tipos[]')

    if not any(lista_cursos) and not any(lista_matriculas):
        return jsonify({"error": "Nenhum dado foi preenchido."}), 400

    csv_data, erros = processar_geracao_csv(lista_cursos, lista_matriculas, lista_tipos)

    if erros:
        return jsonify({"error": " | ".join(erros)}), 400

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=matriculas_sis.csv"}
    )

init_ofertas_routes(app)
app.register_blueprint(shortcut_periodos_bp)
app.register_blueprint(shortcut_inativar_bp)

if __name__ == '__main__':
    app.run(debug=True)