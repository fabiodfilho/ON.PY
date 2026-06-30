from flask import Flask, render_template, request, Response, jsonify
from Controller.csv_controller import processar_geracao_csv

app = Flask(__name__, 
            template_folder='View/templates', 
            static_folder='View/static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gerar-csv', methods=['POST'])
def gerar_csv():
    prosseguir = request.form.get('prosseguir_com_codigos_nao_encontrados', '0') in ('1', 'true', 'True', 'yes', 'sim')

    csv_data, erros, codigos_nao_encontrados = processar_geracao_csv(
        request.form.getlist('cursos[]'),
        request.form.getlist('matriculas[]'),
        prosseguir_com_codigos_nao_encontrados=prosseguir
    )

    if codigos_nao_encontrados and not prosseguir:
        return jsonify({
            "requires_confirmation": True,
            "missing_codes": codigos_nao_encontrados,
            "message": "Alguns códigos não foram encontrados no banco. Deseja prosseguir com os códigos informados?"
        }), 200

    if erros:
        return jsonify({"error": f"Erros na geração do CSV: {'<br>'.join(erros)}"}), 400

    res = Response(csv_data, mimetype="text/csv")
    res.headers["Content-Disposition"] = "attachment; filename=matriculas_sis.csv"
    return res

if __name__ == '__main__':
    app.run(debug=True)