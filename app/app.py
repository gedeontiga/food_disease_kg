import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
# from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from SPARQLWrapper import SPARQLWrapper, JSON
import os
# from models.user import User
# from models.message import Message

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
    
# Dynamic path for images
APP_DIR = os.path.dirname(os.path.abspath(__file__))
FOODS_DIR = os.path.join(APP_DIR, "images", "Foods")
SPARQL_URL = "http://localhost:3030/foodkg/sparql"

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_UPLOAD_FILE_SIZE'] = 16 * 1024 * 1024  # Limite de 16 MB pour les téléchargements
app.config['UPLOAD_FOLDER'] = 'uploads'  # Dossier de stockage des images

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(100))
    profile_picture = db.Column(db.String(200), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'profile_picture': self.profile_picture,
        }

class UserRelation(db.Model):
    user1 = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    user2 = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())  # Ajoutez une colonne de timestamp ici
    message_type = db.Column(db.String(10))
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'message_type': self.message_type,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

# S'assurer que le dossier de téléchargement existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/images/<category>/<filename>')
def serve_image(category, filename):
    dirpath = os.path.join(FOODS_DIR, category)
    if not os.path.exists(os.path.join(dirpath, filename)):
        return jsonify({"error": "Image not found"}), 404
    return send_from_directory(dirpath, filename)

@app.route('/api/foods')
def api_foods():
    try:
        sparql = SPARQLWrapper(SPARQL_URL)
        sparql.setQuery("""
            PREFIX ex: <http://www.semanticweb.org/gedeon/ontologies/2025/4/foods#>
            SELECT ?item ?img WHERE {
                ?item a ex:FoodItem ;
                      ex:image ?img .
            }
        """)
        sparql.setReturnFormat(JSON)
        res = sparql.query().convert()
        items = [
            {'uri': b['item']['value'], 'image': b['img']['value']}
            for b in res['results']['bindings']
        ]
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add default users (Run this once)
@app.before_request
def add_default_users():
    default_users = [
        User(name='User1', email='user1@example.com', password=generate_password_hash('password1')),
        User(name='User2', email='user2@example.com', password=generate_password_hash('password2')),
        User(name='User3', email='user3@example.com', password=generate_password_hash('password3')),
        User(name='User4', email='user4@example.com', password=generate_password_hash('password4'))
    ]
    for user in default_users:
        if not User.query.filter_by(email=user.email).first():
            db.session.add(user)
    db.session.commit()


# Route pour créer un utilisateur
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(name=data.get('name'), email=data.get('email'), password=hashed_password)
    db.session.add(new_user)
    relation1 = User.query.filter_by(email='user1@example.com').first()
    first_relation = UserRelation(user1=new_user.id, user2=relation1.id)
    db.session.add(first_relation)
    relation2 = User.query.filter_by(email='user2@example.com').first()
    second_relation = UserRelation(user1=new_user.id, user2=relation2.id)
    db.session.add(second_relation)
    db.session.commit()
    return jsonify({'message': 'Utilisateur créé avec succès'}), 201


# Route pour authentifier un utilisateur
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user and check_password_hash(user.password, data.get('password')):
        return jsonify({'message': 'Authentification réussie', 'user_id': user.id, 'email': user.email}), 200
    return jsonify({'message': 'Email ou mot de passe incorrect'}), 401

# Route pour récupérer les utilisateurs liés
@app.route('/relations', methods=['GET'])
def get_related_users():
    user_id = request.args.get('user_id')
    relations = UserRelation.query.filter(
        (UserRelation.user1 == user_id) | (UserRelation.user2 == user_id)
    ).all()
    
    related_users = []
    for relation in relations:
        related_user_id = relation.user2 if relation.user1 == int(user_id) else relation.user1
        user = User.query.get(related_user_id)
        related_users.append({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'profile_picture': user.profile_picture
        })
    
    return jsonify(related_users), 200

# Route pour ajouter une relation utilisateur
@app.route('/add_relation', methods=['POST'])
def add_relation():
    try:
        data = request.get_json()
        user1_id = data.get('user1_id')
        user2_email = data.get('user2_email')

        # Vérification que les données existent
        if not user1_id or not user2_email:
            return jsonify({'message': 'Données manquantes'}), 400

        # Récupérer le second utilisateur par son email
        user2 = User.query.filter_by(email=user2_email).first()
        if not user2:
            return jsonify({'message': 'Utilisateur non trouvé'}), 404
        
        # Vérifier que l'utilisateur ne tente pas de créer une relation avec lui-même
        if user1_id == user2.id:
            return jsonify({'message': 'Vous ne pouvez pas créer une relation avec vous-même'}), 400

        # Vérifier si la relation existe déjà
        existing_relation = UserRelation.query.filter_by(user1=user1_id, user2=user2.id).first()
        if existing_relation:
            return jsonify({'message': 'Cette relation existe déjà'}), 409

        # Créer une nouvelle relation
        new_relation = UserRelation(user1=user1_id, user2=user2.id)
        db.session.add(new_relation)
        db.session.commit()

        return jsonify({'message': 'Relation ajoutée avec succès'}), 201

    except Exception as e:
        db.session.rollback()  # Annuler la transaction en cas d'erreur
        return jsonify({'message': f'Erreur serveur: {str(e)}'}), 500

# Ajoutez cette route à votre fichier d'API Flask

@app.route('/profile/delete', methods=['POST'])
def delete_profile():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404

        # Supprimer les relations de l'utilisateur
        UserRelation.query.filter(
            (UserRelation.user1 == user_id) | (UserRelation.user2 == user_id)
        ).delete()

        # Supprimer les messages de l'utilisateur
        Message.query.filter(
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        ).delete()

        # Supprimer la photo de profil si elle existe
        if user.profile_picture and os.path.exists(user.profile_picture):
            os.remove(user.profile_picture)

        # Supprimer l'utilisateur
        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': 'Compte supprimé avec succès'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la suppression : {str(e)}'}), 500

# Route pour envoyer un message
@app.route('/messages/send', methods=['POST'])
def send_message():
    data = request.get_json()
    new_message = Message(
    sender_id = data.get('sender_id'),
    receiver_id = data.get('receiver_id'),
    content = data.get('content'),
    message_type = data.get('message_type')
    )
    db.session.add(new_message)
    db.session.commit()
    return jsonify({'message': 'Message envoyé avec succès'}), 201


# Route pour récupérer les messages entre deux utilisateurs
@app.route('/messages', methods=['GET'])
def get_messages():
    sender_id = request.args.get('sender_id')
    receiver_id = request.args.get('receiver_id')
    # Filtrer les messages pour la conversation entre les deux utilisateurs
    messages = Message.query.filter(
        ((Message.sender_id == sender_id) & (Message.receiver_id == receiver_id)) |
        ((Message.sender_id == receiver_id) & (Message.receiver_id == sender_id))
    ).order_by(Message.timestamp).all()
    return jsonify([message.to_dict() for message in messages]), 200

@app.route('/profile/update', methods=['POST'])
def update_profile():
    data = request.get_json()
    user_id = data.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Mettre à jour le nom
    if 'name' in data:
        user.name = data['name']
    
    # Mettre à jour la photo de profil
    if 'profile_picture' in data:
        user.profile_picture = data['profile_picture']  # Le chemin de l'image
    
    # Mettre à jour le mot de passe (en le hachant)
    # if 'password' in data:
        # user.password = generate_password_hash(data['password'])

    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'}), 200

# Route pour récupérer les informations de profil
@app.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict()), 200

# Exécuter l'application Flask
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Créer la base de données si elle n'existe pas déjà
    app.run(host='0.0.0.0', port=5000, debug=True)
