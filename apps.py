import random
import uuid
import requests
import certifi
import pdfkit
from flask import Flask, render_template_string, redirect, url_for, request, session, render_template, make_response, send_file
from flask_mail import Mail, Message
import sqlite3
import time
import os

app = Flask(__name__)
app.secret_key = "secret_key"

# Configuration email
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='tonadresse@gmail.com',  # Remplacer
    MAIL_PASSWORD='tonmotdepasse',        # Remplacer
    MAIL_DEFAULT_SENDER='tonadresse@gmail.com'  # Remplacer
)
mail = Mail(app)

# Configuration PDFKit avec vérification wkhtmltopdf
WKHTML_PATH = r"C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"
if os.path.exists(WKHTML_PATH):
    config = pdfkit.configuration(wkhtmltopdf=WKHTML_PATH)
else:
    config = None
    print("⚠️ wkhtmltopdf introuvable. Le PDF ne sera pas généré.")

# Simuler une base de données simple
USERS = {"admin": {"nom": "Mamadou Bakayoko", "mdp": "Motrha18(@@)"}}
RESERVATIONS = []
HISTORIQUE = []

# Génération de 100 voitures aléatoires avec prix numérique
VOITURES = []
for i in range(100):
    prix = random.randint(15000, 70000)
    VOITURES.append({
        "id": i + 1,
        "nom": f"Voiture {i+1}",
        "image": f"/static/img/voiture{(i % 10) + 1}.jpg",
        "prix": f"{prix:,} FCFA",
        "prix_numerique": prix,
        "disponible": True
    })

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, voitures=VOITURES)

HTML_TEMPLATE = """
<!doctype html>
<html lang='fr'>
<head>
  <meta charset='utf-8'>
  <title>Location de Voitures</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px; }
    .voiture { background: white; padding: 15px; margin: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); width: 300px; display: inline-block; vertical-align: top; }
    .voiture img { width: 100%; border-radius: 8px; height: 180px; object-fit: cover; }
    .footer { margin-top: 40px; font-size: 16px; }
    h1, h2 { color: #333; }
    .btn { display: inline-block; padding: 10px 15px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; }
    form { margin-top: 20px; }
  </style>
</head>
<body>
  <h2>Bienvenue sur notre site de location des voitures de Qualité</h2>
  <h1>🚗 Location de Voitures (100 Disponibles)</h1>
  {% if session.get('admin') %}
    <p><a href='/logout' class='btn'>Déconnexion (Admin)</a> | <a href='/dashboard' class='btn'>Tableau de bord</a> | <a href='/historique' class='btn'>Historique Paiements</a></p>
  {% endif %}
  {% for voiture in voitures %}
    <div class='voiture'>
      <img src='{{ voiture.image }}' alt='Voiture'>
      <h2>{{ voiture.nom }}</h2>
      <p><strong>Prix:</strong> {{ voiture.prix }}</p>
      <p><strong>Disponibilité:</strong> 
        {% if voiture.disponible %}
          ✅ Oui
        {% else %}
          ❌ Non
        {% endif %}
      </p>
      <form action="/reserver/{{ voiture.id }}" method="post">
        <input type="text" name="nom" placeholder="Votre nom" required><br><br>
        <input type="email" name="email" placeholder="Votre email" required><br><br>
        <input type="date" name="date" required><br><br>
        <input type="tel" name="telephone" placeholder="Téléphone (ex: 71016204)" required><br><br>
        <button type="submit" class="btn">Réserver</button>
      </form>
      <br>
    </div>
  {% endfor %}
  <div class="footer">
    <p>📞 Contactez-nous au <strong>61659149</strong> pour toute question ou réservation spéciale.</p>
    <p><a href="/admin">Espace Admin</a></p>
  </div>
</body>
</html>
"""

@app.route("/reserver/<int:id>", methods=["POST"])
def reserver(id):
    nom = request.form.get("nom")
    email = request.form.get("email")
    date = request.form.get("date")
    telephone = request.form.get("telephone")
    voiture = next((v for v in VOITURES if v["id"] == id), None)

    if voiture and voiture["disponible"]:
        montant = voiture["prix_numerique"]
        transaction_id = str(uuid.uuid4())

        payload = {
            "amount": montant,
            "currency": "XOF",
            "transaction_id": transaction_id,
            "site_id": "105892186",
            "apikey": "158126029767fce03abf3fb2.20570042",
            "description": "Paiement Location Voiture",
            "customer_name": nom,
            "customer_email": email,
            "customer_phone_number": telephone,
            "customer_address": "Bamako",
            "customer_city": "Bamako",
            "customer_country": "ML",
            "channels": "MOBILE_MONEY",
            "notify_url": "http://localhost:5000/retour",
            "return_url": "http://localhost:5000/retour",
            "metadata": "{}"
        }

        try:
            response = requests.post("https://api-checkout.cinetpay.com/v2/payment", json=payload, verify=certifi.where())
            data = response.json()
            if response.status_code == 200 and "payment_url" in data:
                session["paiement"] = {"nom": nom, "email": email, "telephone": telephone, "montant": montant}
                HISTORIQUE.append(session["paiement"])
                voiture["disponible"] = False
                return redirect(data["payment_url"])
            else:
                return f"Erreur API CinetPay : {response.status_code} - {data}"
        except Exception as e:
            return f"Erreur lors de la génération du lien de paiement : {e}"
    return redirect(url_for("index"))

@app.route("/historique")
def historique():
    if not session.get('admin'):
        return redirect(url_for("admin"))
    html = "<h1>Historique des paiements</h1><ul>"
    for h in HISTORIQUE:
        html += f"<li>{h['nom']} - {h['montant']} FCFA - {h['email']} - {h['telephone']}</li>"
    html += "</ul><a href='/'>Retour</a>"
    return html

@app.route("/facture")
def facture():
    if 'paiement' in session:
        html = f"""
        <h1>Facture de Paiement</h1>
        <p>Nom: {session['paiement']['nom']}</p>
        <p>Email: {session['paiement']['email']}</p>
        <p>Téléphone: {session['paiement']['telephone']}</p>
        <p>Montant payé: {session['paiement']['montant']} FCFA</p>
        """
        if config:
            pdf = pdfkit.from_string(html, False, configuration=config)
            with open("facture_temp.pdf", "wb") as f:
                f.write(pdf)
            return send_file("facture_temp.pdf", as_attachment=True)
        else:
            return html
    return redirect(url_for("index"))

@app.route("/retour")
def retour():
    if 'paiement' in session:
        try:
            html_facture = f"""
                <h1>Facture de Paiement</h1>
                <p>Nom: {session['paiement']['nom']}</p>
                <p>Email: {session['paiement']['email']}</p>
                <p>Téléphone: {session['paiement']['telephone']}</p>
                <p>Montant payé: {session['paiement']['montant']} FCFA</p>
            """
            if config:
                pdf_bytes = pdfkit.from_string(html_facture, False, configuration=config)
                msg = Message("Votre Facture - Location de Voiture",
                              recipients=[session['paiement']['email']])
                msg.body = "Merci pour votre paiement. Vous trouverez ci-joint votre facture."
                msg.attach("facture.pdf", "application/pdf", pdf_bytes)
                mail.send(msg)
                print("📧 Facture envoyée à l'adresse:", session['paiement']['email'])
        except Exception as e:
            print("❌ Erreur lors de l'envoi de l'email :", e)
        return "Paiement reçu. La facture a été envoyée par email. <br><br> <a href='/facture'>📄 Télécharger la facture</a>"
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)
