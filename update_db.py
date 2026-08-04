import sqlite3

def run():
    conn = sqlite3.connect('instance/banco.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(clientes)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'cidade' not in columns:
        cursor.execute("ALTER TABLE clientes ADD COLUMN cidade VARCHAR(100)")
    if 'uf' not in columns:
        cursor.execute("ALTER TABLE clientes ADD COLUMN uf VARCHAR(2)")
    if 'cep' not in columns:
        cursor.execute("ALTER TABLE clientes ADD COLUMN cep VARCHAR(20)")
    if 'endereco' not in columns:
        cursor.execute("ALTER TABLE clientes ADD COLUMN endereco VARCHAR(255)")
        
    conn.commit()
    conn.close()
    print("Database updated.")

run()
