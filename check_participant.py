# -*- coding: utf-8 -*-
# Usage: python check_participant.py P3290DEDD
import sqlite3, sys, os

code = sys.argv[1] if len(sys.argv) > 1 else 'P3290DEDD'

for path in ['database/rali_dem.db', 'backend/rali_dem.db']:
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Chercher le participant
        p = cur.execute(
            "SELECT * FROM exp_participants WHERE code_anonyme = ?",
            (code,)
        ).fetchone()

        print(f"Recherche code: '{code}'")
        print(f"Trouve: {'OUI' if p else 'NON'}")

        if p:
            print(f"  id={p['id']} nom={p['nom']} prenom={p['prenom']}")
        else:
            # Afficher tous les codes disponibles
            all_codes = cur.execute(
                "SELECT code_anonyme, nom FROM exp_participants"
            ).fetchall()
            print(f"Codes disponibles:")
            for c in all_codes:
                print(f"  '{c[0]}' | nom='{c[1]}'")
                # Comparer caractere par caractere
                if c[0] and code:
                    match = all(a==b for a,b in zip(c[0], code))
                    print(f"    Longueur: {len(c[0])} vs {len(code)}, Match: {match}")

        conn.close()
        break
