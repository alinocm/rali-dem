import sqlite3
db = r"D:\RALI-DEM\database\rali_dem.db"
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("=== TABLES EXISTANTES ===")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    nb = conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
    print(f"  {t[0]}: {nb} lignes")

print("\n=== track_reponses_adapt ===")
rows = conn.execute("SELECT * FROM track_reponses_adapt LIMIT 5").fetchall()
if rows:
    print("Colonnes:", list(rows[0].keys()))
    for r in rows:
        print(dict(r))
else:
    print("VIDE")

print("\n=== track_sessions_adapt ===")
rows2 = conn.execute("SELECT * FROM track_sessions_adapt LIMIT 5").fetchall()
if rows2:
    for r in rows2:
        print(dict(r))
else:
    print("VIDE")

conn.close()