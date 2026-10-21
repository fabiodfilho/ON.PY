FROM python:3.10-slim

WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

# Expõe a porta interna da aplicação
EXPOSE 8000

# Comando para rodar a aplicação em produção
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8000", "main:app"]