import sqlite3
import os

db_path = 'instance/cjc_sementes.db'
if not os.path.exists(db_path):
    db_path = 'cjc_sementes.db'

if not os.path.exists(db_path):
    print("Database not found!")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, codigo_bling FROM produtos ORDER BY nome")
    produtos = cursor.fetchall()
    print(f"Encontrados {len(produtos)} produtos:")
    for p in produtos:
        print(f"- ID: {p[0]} | Código: {p[2]} | Nome: {p[1]}")
    conn.close()
except Exception as e:
    print(f"Erro: {e}")
