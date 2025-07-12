from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'verallia'  
PASSWORD = "verallia2025"
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('historique'))
        else:
            flash("❌ Mot de passe incorrect.")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/historique', methods=['GET'])
def historique():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Récupération des filtres
    date_filter  = request.args.get('date') or ''
    heure_filter = request.args.get('heure') or ''
    type_filter  = request.args.get('type') or ''
    ligne_filter = request.args.get('ligne') or ''

    # Pagination
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    PAGE_SIZE = 10
    offset = (page - 1) * PAGE_SIZE

    # Requête dynamique avec filtres
    query = "FROM suivi WHERE 1=1"
    params = []

    if date_filter:
        query += " AND DATE(datetime) = ?"
        params.append(date_filter)
    if heure_filter:
        query += " AND TIME(datetime) LIKE ?"
        params.append(f"{heure_filter}%")
    if type_filter:
        query += " AND type = ?"
        params.append(type_filter)
    if ligne_filter:
        query += " AND ligne = ?"
        params.append(ligne_filter)

    # Connexion + curseur
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Nombre total de résultats
    c.execute(f"SELECT COUNT(*) {query}", params)
    total_rows = c.fetchone()[0]
    total_pages = max((total_rows - 1) // PAGE_SIZE + 1, 1)

    # Récupération des données + ID
    c.execute(f"SELECT datetime, type, ligne, photo, id {query} ORDER BY datetime DESC LIMIT ? OFFSET ?", params + [PAGE_SIZE, offset])
    rows = c.fetchall()
    conn.close()

    return render_template('historique.html', data=rows, filters={
        'date': date_filter,
        'heure': heure_filter,
        'type': type_filter,
        'ligne': ligne_filter
    }, page=page, total_pages=total_pages)

@app.route('/delete/<int:id>')
def delete(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT photo FROM suivi WHERE id = ?", (id,))
    photo = c.fetchone()
    if photo and photo[0]:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], photo[0]))
        except:
            pass

    c.execute("DELETE FROM suivi WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("✅ Ligne supprimée.")
    return redirect(url_for('historique'))

    
app.config['UPLOAD_FOLDER'] = 'static/uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS suivi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datetime TEXT,
        type TEXT,
        ligne TEXT,
        photo TEXT
    )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    datetime_val = request.form.get('datetime')
    type_val = request.form.get('type')
    ligne_val = request.form.get('selection')

    photo = request.files['photo']
    if photo.filename != '':
        filename = datetime.now().strftime("%Y%m%d_%H%M%S_") + secure_filename(photo.filename)
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(photo_path)
    else:
        filename = None

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO suivi (datetime, type, ligne, photo) VALUES (?, ?, ?, ?)',
              (datetime_val, type_val, ligne_val, filename))
    conn.commit()
    conn.close()
    flash("✅ Données enregistrées avec succès.")
    return redirect(url_for('index'))
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        type_val = request.form.get('type')
        ligne_val = request.form.get('ligne')
        c.execute("UPDATE suivi SET type = ?, ligne = ? WHERE id = ?", (type_val, ligne_val, id))
        conn.commit()
        conn.close()
        flash("✅ Ligne modifiée.")
        return redirect(url_for('historique'))

    c.execute("SELECT datetime, type, ligne, photo FROM suivi WHERE id = ?", (id,))
    row = c.fetchone()
    conn.close()

    if not row:
        flash("❌ Ligne introuvable.")
        return redirect(url_for('historique'))

    return render_template('edit.html', data={
        'id': id,
        'datetime': row[0],
        'type': row[1],
        'ligne': row[2],
        'photo': row[3]
    })

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

