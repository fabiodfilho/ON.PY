import io
import csv
from Model.excel_engine import BANCO_OFERTAS


def processar_geracao_csv(lista_cursos_input, lista_matriculas_bruta, prosseguir_com_codigos_nao_encontrados=False):
    output = io.StringIO()
    escritor = csv.writer(output)
    escritor.writerow(['course_id', 'user_id', 'role', 'status'])

    erros = []
    codigos_nao_encontrados = []

    for bloco_curso, bloco_matricula in zip(lista_cursos_input, lista_matriculas_bruta):
        codigos = [c.strip() for c in bloco_curso.split('\n') if c.strip()]
        matriculas = [m.strip() for m in bloco_matricula.split('\n') if m.strip()]

        if not codigos:
            erros.append("Bloco de cursos vazio")
            continue
        if not matriculas:
            erros.append("Bloco de matrículas vazio")
            continue

        for m in matriculas:
            for cod in codigos:
                if not cod:
                    erros.append(f"Código inválido: '{cod}'")
                    continue

                sis_id_final = BANCO_OFERTAS.get(cod)
                if sis_id_final is None:
                    if prosseguir_com_codigos_nao_encontrados:
                        escritor.writerow([cod, m, "student", "active"])
                    else:
                        if cod not in codigos_nao_encontrados:
                            codigos_nao_encontrados.append(cod)
                    continue

                escritor.writerow([sis_id_final, m, "student", "active"])

    csv_data = output.getvalue()
    return csv_data, erros, codigos_nao_encontrados