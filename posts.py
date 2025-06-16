from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import uuid
import os
from datetime import datetime
from urllib.parse import urlparse, unquote

# Import initialized Firebase instances and utility functions
from firebase_utils import db, bucket, UPLOAD_FOLDER
from auth import token_required  # Import the decorator

# Create a Blueprint for post-related routes
posts_bp = Blueprint('posts', __name__)


@posts_bp.route('/upload_post', methods=['POST'])
@token_required
def upload_post():
    """
    Handles uploading a new post with an image and caption.
    Requires authentication.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'Сурет жүктелмеген'}), 400

    image = request.files['image']
    caption = request.form.get('caption', '')

    if image.filename == '':
        return jsonify({'error': 'Файл атауы бос'}), 400

    temp_path = None  # Initialize temp_path outside try block for cleanup

    try:
        # Securely generate filename and create a unique name for storage
        filename = secure_filename(image.filename)
        ext = filename.rsplit('.', 1)[-1].lower()
        unique_name = str(uuid.uuid4()) + '.' + ext

        # Save the image to a temporary local directory
        temp_path = os.path.join(UPLOAD_FOLDER, unique_name)
        image.save(temp_path)

        # Upload the image to Firebase Storage
        blob = bucket.blob(f'posts/{unique_name}')
        blob.upload_from_filename(temp_path)
        blob.make_public()  # Make the image publicly accessible
        image_url = blob.public_url

        # Delete the temporary local file
        os.remove(temp_path)

        # Store post data in Firestore
        post_data = {
            'author': request.uid,  # Author UID from the authenticated request
            'caption': caption,
            'image_url': image_url,
            'likes': 0,  # Initialize likes to 0
            'liked_by': [],  # List to store UIDs of users who liked the post
            'created_at': datetime.utcnow()
        }
        db.collection('posts').add(post_data)

        return jsonify({'msg': 'Пост сәтті жүктелді', 'image_url': image_url}), 200

    except Exception as e:
        # Ensure the temporary file is removed even if an error occurs during upload
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500


@posts_bp.route('/feed', methods=['GET'])
def get_feed():
    """
    Retrieves a feed of posts, optionally sorted by likes or creation time.
    """
    try:
        sort_by = request.args.get('sort', 'new')  # Default sort by 'new'

        posts_ref = db.collection('posts')

        if sort_by == 'likes':
            # Order by 'likes' in descending order
            posts_ref = posts_ref.order_by(
                'likes', direction=firestore.Query.DESCENDING)
        else:
            # Default: order by 'created_at' in descending order
            posts_ref = posts_ref.order_by(
                'created_at', direction=firestore.Query.DESCENDING)

        posts = posts_ref.stream()  # Get all posts

        result = []
        for post in posts:
            post_data = post.to_dict()
            result.append({
                'id': post.id,  # Include document ID for actions like like/comment
                'author': post_data.get('author'),
                'caption': post_data.get('caption'),
                'image_url': post_data.get('image_url'),
                'likes': post_data.get('likes', 0),
                'created_at': post_data.get('created_at').isoformat() if post_data.get('created_at') else None
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@posts_bp.route('/my_posts', methods=['GET'])
@token_required
def get_my_posts():
    """
    Retrieves all posts created by the authenticated user.
    """
    try:
        user_id = request.uid  # Get UID from the authenticated request
        posts_ref = db.collection('posts')\
            .where('author', '==', user_id)\
            .order_by('created_at', direction=firestore.Query.DESCENDING)

        posts = posts_ref.stream()

        result = []
        for post in posts:
            post_data = post.to_dict()
            result.append({
                'id': post.id,  # Include document ID for actions like delete/edit
                'caption': post_data.get('caption'),
                'image_url': post_data.get('image_url'),
                'created_at': post_data.get('created_at').isoformat() if 'created_at' in post_data else None,
                'likes': post_data.get('likes', 0)
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@posts_bp.route('/like_post/<post_id>', methods=['POST'])
@token_required
def like_post(post_id):
    """
    Allows an authenticated user to like a post. Prevents multiple likes from the same user.
    """
    try:
        uid = request.uid
        post_ref = db.collection('posts').document(post_id)
        post = post_ref.get()

        if not post.exists:
            return jsonify({'error': 'Пост табылмады'}), 404

        post_data = post.to_dict()
        liked_by = post_data.get('liked_by', [])
        likes = post_data.get('likes', 0)

        # Check if the user has already liked this post
        if uid in liked_by:
            return jsonify({'msg': 'Сіз бұл постқа лайк басқансыз'}), 400

        # Update likes and add user to liked_by list
        liked_by.append(uid)
        likes += 1

        post_ref.update({
            'liked_by': liked_by,
            'likes': likes
        })

        return jsonify({'msg': 'Лайк сәтті басылды', 'total_likes': likes}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@posts_bp.route('/comment/<post_id>', methods=['POST'])
@token_required
def add_comment(post_id):
    """
    Allows an authenticated user to add a comment to a post.
    """
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

        # Add comment to a subcollection 'comments' under the post document
        post_ref.collection('comments').add(comment_data)

        return jsonify({'msg': 'Пікір сәтті қосылды'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@posts_bp.route('/comments/<post_id>', methods=['GET'])
def get_comments(post_id):
    """
    Retrieves all comments for a specific post.
    """
    try:
        post_ref = db.collection('posts').document(post_id)
        if not post_ref.get().exists:
            return jsonify({'error': 'Пост табылмады'}), 404

        # Retrieve comments, ordered by creation time
        comments_ref = post_ref.collection('comments').order_by(
            'created_at', direction=firestore.Query.ASCENDING)
        comments = comments_ref.stream()

        result = []
        for comment in comments:
            data = comment.to_dict()
            result.append({
                'id': comment.id,  # Include comment ID if needed for future operations
                'author': data.get('author'),
                'text': data.get('text'),
                'created_at': data.get('created_at').isoformat() if data.get('created_at') else None
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@posts_bp.route('/delete_post/<post_id>', methods=['DELETE'])
@token_required
def delete_post(post_id):
    """
    Allows an authenticated user to delete their own post.
    Also deletes the associated image from Firebase Storage.
    """
    try:
        uid = request.uid
        post_ref = db.collection('posts').document(post_id)
        post_doc = post_ref.get()

        if not post_doc.exists:
            return jsonify({'error': 'Пост табылмады'}), 404

        post_data = post_doc.to_dict()

        # Only the author can delete their post
        if post_data.get('author') != uid:
            return jsonify({'error': 'Тек өз постыңызды ғана өшіре аласыз'}), 403

        # Delete the image from Storage if it exists
        image_url = post_data.get('image_url')
        if image_url:
            # Extract the file name from the URL
            parsed_url = urlparse(image_url)
            path = unquote(parsed_url.path)
            # The path typically looks like /o/posts%2Funique_name.jpg
            # We need to get 'posts/unique_name.jpg'
            file_name_with_path = path.split('/o/')[-1]
            if '%2F' in file_name_with_path:  # Handle URL encoded slashes
                file_name_with_path = file_name_with_path.replace('%2F', '/')

            blob = bucket.blob(file_name_with_path)
            blob.delete()

        # Delete the post from Firestore
        post_ref.delete()

        return jsonify({'msg': 'Пост сәтті өшірілді'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@posts_bp.route('/edit_post/<post_id>', methods=['POST'])
@token_required
def edit_post(post_id):
    """
    Allows an authenticated user to edit the caption of their own post.
    """
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
        # Only the author can edit their post
        if post_data.get('author') != uid:
            return jsonify({'error': 'Сіз тек өз постыңызды ғана өңдей аласыз'}), 403

        # Update the caption in Firestore
        post_ref.update({'caption': new_caption})

        return jsonify({'msg': 'Сипаттама сәтті жаңартылды'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@posts_bp.route('/search', methods=['GET'])
def search_posts():
    """
    Searches for posts by keyword in their captions.
    Note: Firestore's `where` clause for `in` or `array-contains`
    is better suited for exact matches or array elements.
    For substring search, fetching and filtering client-side is often needed
    unless full-text search solutions like Algolia or Elasticsearch are integrated.
    This implementation fetches all and filters, which might be inefficient for large datasets.
    """
    try:
        keyword = request.args.get('keyword', '').lower().strip()

        if not keyword:
            return jsonify({'error': 'Кілт сөз берілмеген'}), 400

        # Fetch all posts (or a limited number if pagination is implemented)
        # and filter by keyword in caption client-side.
        # For large datasets, consider a dedicated search solution.
        posts_ref = db.collection('posts').order_by(
            'created_at', direction=firestore.Query.DESCENDING)
        posts = posts_ref.stream()

        result = []
        for post in posts:
            post_data = post.to_dict()
            caption = post_data.get('caption', '').lower()

            if keyword in caption:  # Simple substring search
                result.append({
                    'id': post.id,  # Include document ID
                    'author': post_data.get('author'),
                    'caption': post_data.get('caption'),
                    'image_url': post_data.get('image_url'),
                    'likes': post_data.get('likes', 0),
                    'created_at': post_data.get('created_at').isoformat() if post_data.get('created_at') else None
                })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500