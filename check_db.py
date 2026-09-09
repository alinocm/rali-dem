import sqlite3, os

# Chercher la base de données
chemins = [
    'database/rali_dem.db',
    'backend/rali_dem.db',
    'rali_dem.db',
    'backend/database/rali_dem.db',
]

trouve = False
for chemin in chemins:
    if os.path.exists(chemin):
        print(f'Base trouvee : {chemin}')
        conn = sqlite3.connect(chemin)
        cur  = conn.cursor()

        tables = [t[0] for t in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        print(f'Tables ({len(tables)}) : {tables}')
        print()

        # Vérifier les tables expérimentation
        exp_tables = [t for t in tables if t.startswith('exp_')]
        if exp_tables:
            print(f'Tables experimentation : {exp_tables}')
            for t in exp_tables:
                n = cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                print(f'  {t} : {n} ligne(s)')
        else:
            print('ATTENTION : aucune table exp_ trouvee')
            print('Les tables experimentation ne sont pas encore creees.')
            print('Verifiez que init_tables_experimentation() est bien appelee au demarrage.')

        conn.close()
        trouve = True
        break

if not trouve:
    print('Base de donnees non trouvee dans les chemins suivants :')
    for c in chemins:
        print(f'  {c} -> {os.path.abspath(c)}')
    print()
    print('Repertoire courant :', os.getcwd())
    print('Fichiers .db presents :')
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.endswith('.db'):
                print(f'  {os.path.join(root, f)}')
