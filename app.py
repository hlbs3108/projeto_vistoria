from flask import Flask, render_template, request, redirect, flash
import smtplib
import os
import sqlite3
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
app.secret_key = "chave-secreta"
UPLOAD_FOLDER = "uploads"
EMAILS_FILE = "emails.txt"
DB_FILE = "vistorias.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ----------------------------
# Banco de Dados
# ----------------------------
def init_db():
    conexao = sqlite3.connect(DB_FILE)
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vistorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endereco TEXT,
            condominio TEXT,
            cidade TEXT,
            estado TEXT,
            blocos INTEGER,
            andares INTEGER,
            apts_andar INTEGER,
            num_1andar_ini TEXT,
            num_1andar_fim TEXT,
            num_ultandar_ini TEXT,
            num_ultandar_fim TEXT,
            total_apts INTEGER,
            dist_poste_dg TEXT,
            duas_prumadas TEXT,
            dist_prumada1 TEXT,
            dist_prumada2 TEXT,
            sala_terreo TEXT,
            sindico TEXT,
            contato_sindico TEXT,
            area_tecnica TEXT,
            node_hfc TEXT,
            imovel TEXT,
            tecnico TEXT,
            data_envio TEXT
        )
    """)
    conexao.commit()
    conexao.close()

init_db()

# ----------------------------
# Carregar e salvar e-mails
# ----------------------------
def carregar_emails():
    if not os.path.exists(EMAILS_FILE):
        return []
    with open(EMAILS_FILE, "r") as f:
        return [linha.strip() for linha in f if linha.strip()]

def salvar_emails(lista):
    with open(EMAILS_FILE, "w") as f:
        f.write("\n".join(lista))

EMAILS_CADASTRADOS = carregar_emails()
if not EMAILS_CADASTRADOS:
    EMAILS_CADASTRADOS = ["mdu@rimatecnologia.com.br"]
    salvar_emails(EMAILS_CADASTRADOS)

# ----------------------------
# Página inicial
# ----------------------------
@app.route("/")
def index():
    return redirect("/vistoria")

# ----------------------------
# Página de Vistoria
# ----------------------------
@app.route("/vistoria", methods=["GET", "POST"])
def vistoria():
    EMAILS_CADASTRADOS = carregar_emails()

    if request.method == "POST":
        dados = {
            "Endereço": request.form.get("endereco"),
            "Nome do Condomínio": request.form.get("condominio"),
            "Cidade": request.form.get("cidade"),
            "Estado": request.form.get("estado"),
            "Quantidade de blocos": request.form.get("blocos"),
            "Quantidade de Andares": request.form.get("andares"),
            "Apartamentos por andar": request.form.get("apts_andar"),
            "Numeração inicial 1º andar": request.form.get("num_1andar_ini"),
            "Numeração final 1º andar": request.form.get("num_1andar_fim"),
            "Numeração inicial último andar": request.form.get("num_ultandar_ini"),
            "Numeração final último andar": request.form.get("num_ultandar_fim"),
            "Total de apartamentos": request.form.get("total_apts"),
            "Distância Poste → DG": request.form.get("dist_poste_dg"),
            "Duas prumadas?": request.form.get("duas_prumadas"),
            "Distância DG → Prumada 1": request.form.get("dist_prumada1"),
            "Distância DG → Prumada 2": request.form.get("dist_prumada2"),
            "Sala comerciais no térreo?": request.form.get("sala_terreo"),
            "Nome do Síndico": request.form.get("sindico"),
            "Contato do Síndico": request.form.get("contato_sindico"),
            "Área Técnica": request.form.get("area_tecnica"),
            "Node HFC": request.form.get("node_hfc"),
            "Imóvel": request.form.get("imovel"),
            "Técnico responsável": request.form.get("tecnico")
        }

        emails_selecionados = request.form.getlist("emails")
        novo_email = request.form.get("novo_email")
        if novo_email and novo_email not in EMAILS_CADASTRADOS:
            EMAILS_CADASTRADOS.append(novo_email)
            salvar_emails(EMAILS_CADASTRADOS)
        if novo_email:
            emails_selecionados.append(novo_email)

        # Anexos
        anexos = []
        for campo in ["croqui", "planilha", "mapa"]:
            arquivo = request.files.get(campo)
            if arquivo and arquivo.filename:
                caminho = os.path.join(UPLOAD_FOLDER, arquivo.filename)
                arquivo.save(caminho)
                anexos.append(caminho)

        try:
            salvar_vistoria_no_banco(dados)
            enviar_email(dados, anexos, emails_selecionados)
            flash("✅ Vistoria enviada e salva com sucesso!", "success")
        except Exception as e:
            flash(f"❌ Erro ao enviar vistoria: {str(e)}", "danger")

        return redirect("/vistoria")

    return render_template("vistoria.html", emails=EMAILS_CADASTRADOS)

# ----------------------------
# Salvar vistoria no banco
# ----------------------------
def salvar_vistoria_no_banco(dados):
    conexao = sqlite3.connect(DB_FILE)
    cursor = conexao.cursor()
    cursor.execute("""
        INSERT INTO vistorias (
            endereco, condominio, cidade, estado, blocos, andares, apts_andar,
            num_1andar_ini, num_1andar_fim, num_ultandar_ini, num_ultandar_fim,
            total_apts, dist_poste_dg, duas_prumadas, dist_prumada1, dist_prumada2,
            sala_terreo, sindico, contato_sindico, area_tecnica, node_hfc, imovel,
            tecnico, data_envio
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        dados["Endereço"], dados["Nome do Condomínio"], dados["Cidade"], dados["Estado"],
        dados["Quantidade de blocos"], dados["Quantidade de Andares"],
        dados["Apartamentos por andar"], dados["Numeração inicial 1º andar"],
        dados["Numeração final 1º andar"], dados["Numeração inicial último andar"],
        dados["Numeração final último andar"], dados["Total de apartamentos"],
        dados["Distância Poste → DG"], dados["Duas prumadas?"], dados["Distância DG → Prumada 1"],
        dados["Distância DG → Prumada 2"], dados["Sala comerciais no térreo?"], dados["Nome do Síndico"],
        dados["Contato do Síndico"], dados["Área Técnica"], dados["Node HFC"], dados["Imóvel"],
        dados["Técnico responsável"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conexao.commit()
    conexao.close()

# ----------------------------
# Gerenciamento de e-mails
# ----------------------------
@app.route("/emails", methods=["GET", "POST"])
def gerenciar_emails():
    EMAILS_CADASTRADOS = carregar_emails()

    if request.method == "POST":
        novo = request.form.get("novo_email")
        remover = request.form.get("remover")
        if novo:
            if novo not in EMAILS_CADASTRADOS:
                EMAILS_CADASTRADOS.append(novo)
                salvar_emails(EMAILS_CADASTRADOS)
                flash("✅ E-mail adicionado com sucesso!", "success")
            else:
                flash("⚠️ E-mail já cadastrado!", "warning")
        if remover:
            if remover in EMAILS_CADASTRADOS:
                EMAILS_CADASTRADOS.remove(remover)
                salvar_emails(EMAILS_CADASTRADOS)
                flash("🗑️ E-mail removido com sucesso!", "info")
        return redirect("/emails")

    return render_template("emails.html", emails=EMAILS_CADASTRADOS)

# ----------------------------
# Histórico de Vistorias
# ----------------------------
@app.route("/historico")
def historico():
    conexao = sqlite3.connect(DB_FILE)
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT id, condominio, cidade, estado, tecnico, data_envio
        FROM vistorias ORDER BY data_envio DESC
    """)
    vistorias = cursor.fetchall()
    conexao.close()
    return render_template("historico.html", vistorias=vistorias)

# ----------------------------
# Envio de e-mail
# ----------------------------
def enviar_email(dados, anexos, destinatarios):
    remetente = "mdu.pr.interior@gmail.com"
    senha_app = "adlz guui jhak weti"

    msg = MIMEMultipart()
    msg["From"] = remetente
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = f"Nova Vistoria - {dados['Nome do Condomínio']}"

    corpo = "\n".join([f"{k}: {v}" for k, v in dados.items()])
    msg.attach(MIMEText(corpo, "plain"))

    for anexo in anexos:
        with open(anexo, "rb") as f:
            parte = MIMEBase("application", "octet-stream")
            parte.set_payload(f.read())
            encoders.encode_base64(parte)
            parte.add_header("Content-Disposition", f"attachment; filename={os.path.basename(anexo)}")
            msg.attach(parte)

    with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
        servidor.starttls()
        servidor.login(remetente, senha_app)
        servidor.send_message(msg)

# ----------------------------
# Inicialização
# ----------------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
