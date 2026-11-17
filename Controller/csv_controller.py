import io
import csv

def processar_geracao_csv(lista_cursos_input, lista_matriculas_bruta, lista_tipos_input):
    output = io.StringIO()
    escritor = csv.writer(output)
    
    escritor.writerow(['course_id', 'user_id', 'role', 'status'])

    erros = []

    for bloco_curso, bloco_matricula, papel in zip(lista_cursos_input, lista_matriculas_bruta, lista_tipos_input):
        codigos = [c.strip() for c in bloco_curso.split('\n') if c.strip()]
        matriculas = [m.strip() for m in bloco_matricula.split('\n') if m.strip()]
        
        role = papel.strip() if papel else ""

        if not codigos:
            erros.append("Bloco de cursos vazio")
            continue
        if not matriculas:
            erros.append("Bloco de matrículas vazio")
            continue
        if not role:
            erros.append("Nenhum papel selecionado para o bloco")
            continue

        for m in matriculas:
            for cod in codigos:
                if not cod:
                    erros.append("Código de curso inválido encontrado")
                    continue

                escritor.writerow([cod, m, role, "active"])

    csv_data = output.getvalue()
    
    return csv_data, erros