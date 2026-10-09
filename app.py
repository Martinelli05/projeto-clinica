import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "clinica-vida-chave-secreta"
DB = "clinica.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS medicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            crm TEXT NOT NULL UNIQUE,
            especialidade TEXT NOT NULL,
            telefone TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            data_nascimento TEXT NOT NULL,
            telefone TEXT NOT NULL,
            endereco TEXT NOT NULL
        )
    """)
    existe = conn.execute(
        "SELECT id FROM usuarios WHERE email = ?", ("admin@clinicavida.com",)
    ).fetchone()
    if not existe:
        conn.execute(
            "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
            ("Administrador", "admin@clinicavida.com", generate_password_hash("123456")),
        )
    conn.commit()
    conn.close()


# Garante que as tabelas existam sempre que o app iniciar
init_db()


def login_required(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Faça login para acessar esta página.", "erro")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorada


# ---------------------- LOGIN / SAIR ----------------------
@app.route("/")
def index():
    if "usuario_id" in session:
        return redirect(url_for("painel"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        senha = request.form["senha"]

        conn = get_db()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if usuario and check_password_hash(usuario["senha"], senha):
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]
            return redirect(url_for("painel"))

        flash("E-mail ou senha inválidos.", "erro")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/sair")
def sair():
    session.clear()
    flash("Sessão encerrada com sucesso.", "sucesso")
    return redirect(url_for("login"))


@app.route("/painel")
@login_required
def painel():
    conn = get_db()
    total_usuarios = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    total_medicos = conn.execute("SELECT COUNT(*) FROM medicos").fetchone()[0]
    total_pacientes = conn.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]
    conn.close()
    return render_template(
        "painel.html",
        total_usuarios=total_usuarios,
        total_medicos=total_medicos,
        total_pacientes=total_pacientes,
    )


# ---------------------- USUÁRIOS ----------------------
@app.route("/usuarios", methods=["GET", "POST"])
@login_required
def usuarios():
    conn = get_db()
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip()
        senha = request.form["senha"]
        try:
            conn.execute(
                "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
                (nome, email, generate_password_hash(senha)),
            )
            conn.commit()
            flash("Usuário cadastrado com sucesso!", "sucesso")
        except sqlite3.IntegrityError:
            flash("Já existe um usuário com esse e-mail.", "erro")
        conn.close()
        return redirect(url_for("usuarios"))

    lista = conn.execute("SELECT * FROM usuarios ORDER BY nome").fetchall()
    conn.close()
    return render_template("usuarios.html", usuarios=lista, editando=None)


@app.route("/usuarios/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_usuario(id):
    conn = get_db()
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip()
        senha = request.form["senha"]
        try:
            if senha:
                conn.execute(
                    "UPDATE usuarios SET nome=?, email=?, senha=? WHERE id=?",
                    (nome, email, generate_password_hash(senha), id),
                )
            else:
                conn.execute(
                    "UPDATE usuarios SET nome=?, email=? WHERE id=?",
                    (nome, email, id),
                )
            conn.commit()
            flash("Usuário atualizado com sucesso!", "sucesso")
        except sqlite3.IntegrityError:
            flash("Já existe um usuário com esse e-mail.", "erro")
        conn.close()
        return redirect(url_for("usuarios"))

    usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (id,)).fetchone()
    lista = conn.execute("SELECT * FROM usuarios ORDER BY nome").fetchall()
    conn.close()
    if not usuario:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("usuarios"))
    return render_template("usuarios.html", usuarios=lista, editando=usuario)


@app.route("/usuarios/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_usuario(id):
    if id == session["usuario_id"]:
        flash("Você não pode excluir o usuário que está logado.", "erro")
        return redirect(url_for("usuarios"))
    conn = get_db()
    conn.execute("DELETE FROM usuarios WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Usuário excluído com sucesso!", "sucesso")
    return redirect(url_for("usuarios"))


# ---------------------- MÉDICOS ----------------------
@app.route("/medicos", methods=["GET", "POST"])
@login_required
def medicos():
    conn = get_db()
    if request.method == "POST":
        try:
            conn.execute(
                "INSERT INTO medicos (nome, crm, especialidade, telefone) VALUES (?, ?, ?, ?)",
                (
                    request.form["nome"].strip(),
                    request.form["crm"].strip(),
                    request.form["especialidade"].strip(),
                    request.form["telefone"].strip(),
                ),
            )
            conn.commit()
            flash("Médico cadastrado com sucesso!", "sucesso")
        except sqlite3.IntegrityError:
            flash("Já existe um médico com esse CRM.", "erro")
        conn.close()
        return redirect(url_for("medicos"))

    lista = conn.execute("SELECT * FROM medicos ORDER BY nome").fetchall()
    conn.close()
    return render_template("medicos.html", medicos=lista, editando=None)


@app.route("/medicos/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_medico(id):
    conn = get_db()
    if request.method == "POST":
        try:
            conn.execute(
                "UPDATE medicos SET nome=?, crm=?, especialidade=?, telefone=? WHERE id=?",
                (
                    request.form["nome"].strip(),
                    request.form["crm"].strip(),
                    request.form["especialidade"].strip(),
                    request.form["telefone"].strip(),
                    id,
                ),
            )
            conn.commit()
            flash("Médico atualizado com sucesso!", "sucesso")
        except sqlite3.IntegrityError:
            flash("Já existe um médico com esse CRM.", "erro")
        conn.close()
        return redirect(url_for("medicos"))

    medico = conn.execute("SELECT * FROM medicos WHERE id = ?", (id,)).fetchone()
    lista = conn.execute("SELECT * FROM medicos ORDER BY nome").fetchall()
    conn.close()
    if not medico:
        flash("Médico não encontrado.", "erro")
        return redirect(url_for("medicos"))
    return render_template("medicos.html", medicos=lista, editando=medico)


@app.route("/medicos/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_medico(id):
    conn = get_db()
    conn.execute("DELETE FROM medicos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Médico excluído com sucesso!", "sucesso")
    return redirect(url_for("medicos"))


# ---------------------- PACIENTES (QUESTÃO 8) ----------------------
@app.route("/pacientes", methods=["GET", "POST"])
@login_required
def pacientes():
    conn = get_db()
    if request.method == "POST":
        try:
            conn.execute(
                """INSERT INTO pacientes (nome, cpf, data_nascimento, telefone, endereco)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    request.form["nome"].strip(),
                    request.form["cpf"].strip(),
                    request.form["data_nascimento"],
                    request.form["telefone"].strip(),
                    request.form["endereco"].strip(),
                ),
            )
            conn.commit()
            flash("Paciente cadastrado com sucesso!", "sucesso")
        except sqlite3.IntegrityError:
            flash("Já existe um paciente com esse CPF.", "erro")
        conn.close()
        return redirect(url_for("pacientes"))

    lista = conn.execute("SELECT * FROM pacientes ORDER BY nome").fetchall()
    conn.close()
    return render_template("pacientes.html", pacientes=lista, editando=None)


@app.route("/pacientes/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_paciente(id):
    conn = get_db()
    if request.method == "POST":
        try:
            conn.execute(
                """UPDATE pacientes
                   SET nome=?, cpf=?, data_nascimento=?, telefone=?, endereco=?
                   WHERE id=?""",
                (
                    request.form["nome"].strip(),
                    request.form["cpf"].strip(),
                    request.form["data_nascimento"],
                    request.form["telefone"].strip(),
                    request.form["endereco"].strip(),
                    id,
                ),
            )
            conn.commit()
            flash("Paciente atualizado com sucesso!", "sucesso")
        except sqlite3.IntegrityError:
            flash("Já existe um paciente com esse CPF.", "erro")
        conn.close()
        return redirect(url_for("pacientes"))

    paciente = conn.execute("SELECT * FROM pacientes WHERE id = ?", (id,)).fetchone()
    lista = conn.execute("SELECT * FROM pacientes ORDER BY nome").fetchall()
    conn.close()
    if not paciente:
        flash("Paciente não encontrado.", "erro")
        return redirect(url_for("pacientes"))
    return render_template("pacientes.html", pacientes=lista, editando=paciente)


@app.route("/pacientes/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_paciente(id):
    conn = get_db()
    conn.execute("DELETE FROM pacientes WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Paciente excluído com sucesso!", "sucesso")
    return redirect(url_for("pacientes"))


# ---------------------- AGENDAMENTOS ----------------------
@app.route("/agendamentos")
@login_required
def agendamentos():
    return render_template("agendamentos.html")


if __name__ == "__main__":
    app.run(debug=True)