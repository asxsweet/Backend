from flask import Flask, request, jsonify
from firebase_admin import storage
from firebase_admin import credentials, firestore, storage
import firebase_admin
import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore
from functools import wraps
from firebase_admin import auth as admin_auth
from werkzeug.utils import secure_filename
import uuid
import os
from datetime import datetime

app = Flask(__name__)

# Firebase Pyrebase config
firebaseConfig = {
    "apiKey": "AIzaSyDQ1HiMl7-5pB5KB_tQjaSCz1Z4iW2LCB8",
    "authDomain": "post-147cb.firebaseapp.com",
    "projectId": "post-147cb",
    "storageBucket": "post-147cb.firebasestorage.app",
    "messagingSenderId": "89814444873",
    "appId": "1:89814444873:web:3a0528574a03e4fc470898",
    "measurementId": "G-HYQVXGL65P",
    "databaseURL": ""
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

# Firebase Admin SDK
cred = credentials.Certificate("post.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'post-147cb.firebasestorage.app'
})
db = firestore.client()

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data['email']
    password = data['password']
    name = data.get('name', '')

    try:
        user = auth.create_user_with_email_and_password(email, password)
        uid = user['localId']
        db.collection('users').document(uid).set({
            'email': email,
            'name': name
        })
        return jsonify({"msg": "Тіркелу сәтті өтті"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    try:
        user = auth.sign_in_with_email_and_password(email, password)
        token = user['idToken']
        uid = user['localId']

        # Firestore ішіндегі қолданушы құжатын жаңарту
        db.collection('users').document(uid).update({
            'last_login': datetime.utcnow()
        })

        return jsonify({
            "msg": "Кіру сәтті өтті",
            "idToken": token,
            "uid": uid
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 401


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Токенді "Authorization" хэдерінен іздейміз
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split(" ")
            if len(parts) == 2 and parts[0] == "Bearer":
                token = parts[1]

        if not token:
            return jsonify({'message': 'Токен берілмеген'}), 401

        try:
            # Firebase Admin арқылы токенді тексеру
            decoded_token = admin_auth.verify_id_token(token)
            request.uid = decoded_token['uid']  # UID сақтаймыз
        except Exception as e:
            return jsonify({'message': 'Токен жарамсыз', 'error': str(e)}), 401

        return f(*args, **kwargs)
    return decorated
 
@app.route('/protected', methods=['GET'])
@token_required
def protected():
    return jsonify({
        'message': 'Бұл қорғалған маршрут',
        'uid': request.uid
    }), 200

@app.route('/upload_post', methods=['POST'])
@token_required
def upload_post():
    if 'image' not in request.files:
        return jsonify({'error': 'Сурет жүктелмеген'}), 400

    image = request.files['image']
    caption = request.form.get('caption', '')
    if image.filename == '':
        return jsonify({'error': 'Файл атауы бос'}), 400

    try:
        filename = secure_filename(image.filename)
        ext = filename.rsplit('.', 1)[-1]
        unique_name = str(uuid.uuid4()) + '.' + ext
        temp_path = os.path.join('static', unique_name)
        image.save(temp_path)

        # Firebase Storage-қа жүктеу
        bucket = storage.bucket()
        blob = bucket.blob(f'posts/{unique_name}')
        blob.upload_from_filename(temp_path)
        blob.make_public()
        image_url = blob.public_url

        # Жергілікті файлды өшіру
        os.remove(temp_path)

        # Firestore-ға пост дерегін жазу
        post_data = {
            'author': request.uid,
            'caption': caption,
            'image_url': image_url,
            'created_at': datetime.utcnow()
        }
        db.collection('posts').add(post_data)

        return jsonify({'msg': 'Пост сәтті жүктелді', 'image_url': image_url}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/feed', methods=['GET'])
def get_feed():
    try:
        sort_by = request.args.get('sort', 'new')

        posts_ref = db.collection('posts')

        if sort_by == 'likes':
            posts_ref = posts_ref.order_by('likes', direction=firestore.Query.DESCENDING)
        else:
            posts_ref = posts_ref.order_by('created_at', direction=firestore.Query.DESCENDING)

        posts = posts_ref.stream()

        result = []
        for post in posts:
            post_data = post.to_dict()
            result.append({
                'author': post_data.get('author'),
                'caption': post_data.get('caption'),
                'image_url': post_data.get('image_url'),
                'likes': post_data.get('likes', 0),
                'created_at': post_data.get('created_at').isoformat() if post_data.get('created_at') else None
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    
@app.route('/my_posts', methods=['GET'])
@token_required
def get_my_posts():
    try:
        user_id = request.uid  # Токеннен UID алынды
        posts_ref = db.collection('posts')\
            .where('author', '==', user_id)\
            .order_by('created_at', direction=firestore.Query.DESCENDING)

        posts = posts_ref.stream()

        result = []
        for post in posts:
            post_data = post.to_dict()
            result.append({
                'caption': post_data.get('caption'),
                'image_url': post_data.get('image_url'),
                'created_at': post_data.get('created_at').isoformat() if 'created_at' in post_data else None,
                'likes': post_data.get('likes', 0)

            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/like_post/<post_id>', methods=['POST'])
@token_required
def like_post(post_id):
    try:
        uid = request.uid
        post_ref = db.collection('posts').document(post_id)
        post = post_ref.get()

        if not post.exists:
            return jsonify({'error': 'Пост табылмады'}), 404

        post_data = post.to_dict()
        liked_by = post_data.get('liked_by', [])
        likes = post_data.get('likes', 0)

        if uid in liked_by:
            return jsonify({'msg': 'Сіз бұл постқа лайк басқансыз'}), 400

        # Лайкты жаңарту
        liked_by.append(uid)
        likes += 1

        post_ref.update({
            'liked_by': liked_by,
            'likes': likes
        })

        return jsonify({'msg': 'Лайк сәтті басылды', 'total_likes': likes}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/comment/<post_id>', methods=['POST'])
@token_required
def add_comment(post_id):
    try:
        user_id = request.uid
        comment_text = request.json.get('text', '').strip()

        if not comment_text:
            return jsonify({'error': 'Пікір бос болмауы керек'}), 400

        post_ref = db.collection('posts').document(post_id)
        if not post_ref.get().exists:
            return jsonify({'error': 'Пост табылмады'}), 404

        comment_data = {
            'author': user_id,
            'text': comment_text,
            'created_at': datetime.utcnow()
        }

        post_ref.collection('comments').add(comment_data)

        return jsonify({'msg': 'Пікір сәтті қосылды'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/comments/<post_id>', methods=['GET'])
def get_comments(post_id):
    try:
        post_ref = db.collection('posts').document(post_id)
        if not post_ref.get().exists:
            return jsonify({'error': 'Пост табылмады'}), 404

        comments_ref = post_ref.collection('comments').order_by('created_at', direction=firestore.Query.ASCENDING)
        comments = comments_ref.stream()

        result = []
        for comment in comments:
            data = comment.to_dict()
            result.append({
                'author': data.get('author'),
                'text': data.get('text'),
                'created_at': data.get('created_at').isoformat() if data.get('created_at') else None
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/profile/<uid>', methods=['GET'])
def get_profile(uid):
    try:
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({'error': 'Қолданушы табылмады'}), 404

        user_data = user_doc.to_dict()

        return jsonify({
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            'photo_url': user_data.get('photo_url', None)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/edit_profile', methods=['POST'])
@token_required
def edit_profile():
    try:
        uid = request.uid
        data = request.json

        name = data.get('name')
        photo_url = data.get('photo_url')

        update_data = {}
        if name:
            update_data['name'] = name
        if photo_url:
            update_data['photo_url'] = photo_url

        if not update_data:
            return jsonify({'error': 'Өзгерту үшін деректер берілмеген'}), 400

        user_ref = db.collection('users').document(uid)
        user_ref.update(update_data)

        return jsonify({'msg': 'Профиль сәтті жаңартылды'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_post/<post_id>', methods=['DELETE'])
@token_required
def delete_post(post_id):
    try:
        uid = request.uid
        post_ref = db.collection('posts').document(post_id)
        post_doc = post_ref.get()

        if not post_doc.exists:
            return jsonify({'error': 'Пост табылмады'}), 404

        post_data = post_doc.to_dict()

        # Тек автор ғана өшіре алады
        if post_data.get('author') != uid:
            return jsonify({'error': 'Тек өз постыңызды ғана өшіре аласыз'}), 403

        # Суретті Storage-тен өшіру
        image_url = post_data.get('image_url')
        if image_url:
            # URL ішінен файл атын бөліп алу
            from urllib.parse import urlparse, unquote
            parsed_url = urlparse(image_url)
            path = unquote(parsed_url.path)
            file_name = path.split('/')[-1]
            blob = storage.bucket().blob(f'posts/{file_name}')
            blob.delete()

        # Firestore-дан постты өшіру
        post_ref.delete()

        return jsonify({'msg': 'Пост сәтті өшірілді'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/edit_post/<post_id>', methods=['POST'])
@token_required
def edit_post(post_id):
    try:
        uid = request.uid
        data = request.json
        new_caption = data.get('caption', '').strip()

        if not new_caption:
            return jsonify({'error': 'Сипаттама бос болмауы керек'}), 400

        post_ref = db.collection('posts').document(post_id)
        post_doc = post_ref.get()

        if not post_doc.exists:
            return jsonify({'error': 'Пост табылмады'}), 404

        post_data = post_doc.to_dict()
        if post_data.get('author') != uid:
            return jsonify({'error': 'Сіз тек өз постыңызды ғана өңдей аласыз'}), 403

        post_ref.update({'caption': new_caption})

        return jsonify({'msg': 'Сипаттама сәтті жаңартылды'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/search', methods=['GET'])
def search_posts():
    try:
        keyword = request.args.get('keyword', '').lower().strip()

        if not keyword:
            return jsonify({'error': 'Кілт сөз берілмеген'}), 400

        posts_ref = db.collection('posts').order_by('created_at', direction=firestore.Query.DESCENDING)
        posts = posts_ref.stream()

        result = []
        for post in posts:
            post_data = post.to_dict()
            caption = post_data.get('caption', '').lower()

            if keyword in caption:
                result.append({
                    'author': post_data.get('author'),
                    'caption': post_data.get('caption'),
                    'image_url': post_data.get('image_url'),
                    'likes': post_data.get('likes', 0),
                    'created_at': post_data.get('created_at').isoformat() if post_data.get('created_at') else None
                })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Қате сұраныс'}), 400

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({'error': 'Авторизация қажет'}), 401

@app.errorhandler(403)
def forbidden(e):
    return jsonify({'error': 'Рұқсат жоқ'}), 403

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Бет табылмады'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Сервер қатесі'}), 500



if __name__ == '__main__':
    app.run(debug=True)
