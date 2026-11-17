import os
import pandas as pd

def carregar_banco_dados():
    caminho_db = os.path.join('Model', 'BD-OFERTAS-261.1.xlsx')
    banco_procura = {}
    
    try:
        df = pd.read_excel(caminho_db)
        df.columns = df.columns.str.strip()

        titulo_col = next((c for c in df.columns if c.lower().replace('_','').replace(' ','') in ['título','titulo','title','nomecurso','nomecurso']), None)
        sis_id_col = next((c for c in df.columns if c.lower().replace('_','') in ['sisid','sisidcode']), None)

        if not titulo_col or not sis_id_col:
            return {}

        for _, linha in df.iterrows():
            titulo_completo = str(linha.get(titulo_col, '')).strip()
            sis_id = str(linha.get(sis_id_col, '')).strip()
            codigo_6_digitos = titulo_completo[:6]

            if codigo_6_digitos.isdigit() and sis_id:
                banco_procura[codigo_6_digitos] = sis_id
    except Exception as e:
        print(f"Erro Model: {e}")
    
    return banco_procura

BANCO_OFERTAS = carregar_banco_dados()
print(f"--- BANCO CARREGADO ({len(BANCO_OFERTAS)} itens) ---")