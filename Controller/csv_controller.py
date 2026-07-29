import io
import csv

def processar_geracao_csv(lista_cursos_input, lista_matriculas_bruta, lista_tipos_input):
    output = io.StringIO()
    escritor = csv.writer(output)
    
    # Cabeçalho padrão para importação no Canvas
    escritor.writerow(['course_id', 'user_id', 'role', 'status'])

    erros = []

    # Iteramos sobre os 3 arrays simultaneamente
    for bloco_curso, bloco_matricula, papel in zip(lista_cursos_input, lista_matriculas_bruta, lista_tipos_input):
        codigos = [c.strip() for c in bloco_curso.split('\n') if c.strip()]
        matriculas = [m.strip() for m in bloco_matricula.split('\n') if m.strip()]
        
        # Pega a string única do papel (ex: "student")
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

                # Escreve a linha diretamente com o único papel do bloco
                escritor.writerow([cod, m, role, "active"])

    csv_data = output.getvalue()
    
    return csv_data, erros