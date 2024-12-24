import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity,unset_jwt_cookies,get_jwt,verify_jwt_in_request,get_csrf_token
import os
import pymysql
from datetime import datetime
from flask_cors import CORS
import logging

app = Flask(__name__)


load_dotenv()
GOOGLE_CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']
GOOGLE_SECRET_KEY = os.environ['GOOGLE_CLIENT_SECRET']


app.config['CORS_HEADERS'] = 'Content-Type'
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])


app.config['JWT_SECRET_KEY'] = 'JWT_SECRET_KEY'
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
jwt = JWTManager(app)


logging.getLogger('flask_cors').level = logging.DEBUG
# Enable token blacklisting
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']

blacklisted_tokens = set()

@jwt.token_in_blocklist_loader
def check_if_token_in_blacklist(jwt_header, jwt_payload):
    return jwt_payload['jti'] in blacklisted_tokens

def db_connection():
    conn = None
    try:
        conn = pymysql.connect(
            host='localhost',
            database='mygram',
            user='root',
            password=os.environ['DB_PASSWORD'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.MySQLError as e:
        print(e)
    return conn

@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    print("logout called")
    verify_jwt_in_request()
    jti = get_jwt()['jti']
    blacklisted_tokens.add(jti)  # Blacklist the token
    response = jsonify({'message': 'Successfully logged out'})
    unset_jwt_cookies(response)  # Clear the cookie
    return response

@app.route('/google_login', methods=['POST'])
def login():
    auth_code = request.get_json().get('code')
    print(auth_code)

    data = {
        'code': auth_code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_SECRET_KEY,
        'redirect_uri': 'postmessage',
        'grant_type': 'authorization_code'
    }


    response = requests.post('https://oauth2.googleapis.com/token', data=data)
    if response.status_code != 200:
        return jsonify({"msg": "Failed to obtain access token"}), 401

    response_data = response.json()
    access_token = response_data.get('access_token')

    if not access_token:
        return jsonify({"msg": "No access token found"}), 401

    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    user_info = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers=headers).json()


    jwt_token = create_access_token(identity=user_info['email'])
    response = jsonify(user=user_info)


    response.set_cookie('access_token_cookie', value=jwt_token, secure=False, httponly=True)
    csrf_token = get_csrf_token(jwt_token)
    response.set_cookie('csrf_access_token', csrf_token, httponly=False, secure=False)

    return response, 200


@app.route('/protected', methods=['GET'])
def protected():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"message": "Token is missing!"}), 401

    # Here, add your token verification logic
    try:
        # Assume verify_token is a function that verifies your token
        user = verify_token(token.split(" ")[1])  # Strip 'Bearer ' from token
    except Exception as e:
        print("Token verification failed:", e)
        return jsonify({"message": "Token is invalid!"}), 401

    return jsonify({"message": "Access granted", "user": user}), 200

@app.route('/users', methods=['GET', 'POST'])
def users():
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'GET':
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        conn.commit()
        return jsonify(rows)

    if request.method == 'POST':
        name = request.get_json().get('name')
        email = request.get_json().get('email')
        sql = """INSERT INTO users(name, email) VALUES(%s, %s)"""
        cursor.execute(sql, (name, email))
        conn.commit()
        return jsonify({"message": "User added"})


@app.route('/users/<int:id>', methods=['GET'])
def user_by_id(id):
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'GET':
        sql = """SELECT * FROM users WHERE id = %s"""
        cursor.execute(sql, (id,))
        row = cursor.fetchone()
        conn.commit()
        return jsonify(row)



@app.route('/me', methods=['GET'])
@jwt_required()
def get_user_info():
    conn = db_connection()
    cursor = conn.cursor()
    current_user = get_jwt_identity()
    print(current_user)
    sql = "SELECT name from users WHERE email = %s"
    cursor.execute(sql,  current_user)
    row = cursor.fetchone()
    conn.commit()
    return jsonify(row)



@app.route('/posts', methods=['GET', 'POST', 'OPTIONS'])
@jwt_required()
def posts():
    conn = db_connection()
    cursor = conn.cursor()
    print(request.method)


    if request.method == 'GET':
        jwt_token = request.cookies.get('access_token_cookie')  # Demonstration how to get the cookie
        verify_jwt_in_request()
        current_user = get_jwt_identity()
        print(current_user)
        userid = request.args.get('userid')
        print(userid)
        sql1 = """SELECT id from users WHERE email = %s"""
        cursor.execute(sql1, (current_user,))
        user_rows = cursor.fetchone()
        print(user_rows)
        userid = user_rows['id']
        sql = """SELECT title, DATE_FORMAT(created, '%%M %%d') AS formatted_date, LEFT(description, 30) AS short_description, id FROM posts WHERE user_id = %s"""
        cursor.execute(sql, (userid,))
        rows = cursor.fetchall()
        conn.commit()
        return jsonify(rows)

    if request.method == "OPTIONS":
        return jsonify({"msg": "Options  allowed"}), 200




    if request.method == 'POST':
        print("I am here")

        verify_jwt_in_request()
        current_user = get_jwt_identity()
        print("current_user", current_user)
        sql1="""SELECT id from users WHERE email = %s"""
        cursor.execute(sql1,(current_user))
        userid = cursor.fetchone()


        data = request.get_json()
        title = data.get('title')
        description = data.get('description')

        print(userid)
        now = datetime.now()
        formatted_datetime = now.strftime('%Y-%m-%d %H:%M:%S')
        sql = """INSERT INTO posts(title, description, created, user_id) VALUES(%s, %s, %s, %s)"""
        cursor.execute(sql, (title, description, formatted_datetime, userid['id']))
        conn.commit()
        return jsonify({"message": "Post Added"})



@app.route('/posts/<int:id>', methods=['GET'])
def post_by_id(id):
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'GET':
        sql = """SELECT posts.title, posts.description, posts.created, COUNT(DISTINCT comments.id) AS num_comments, COUNT(DISTINCT post_likes.id) AS num_likes
                 FROM posts 
                 LEFT JOIN comments ON posts.id = comments.post_id
                 LEFT JOIN post_likes ON posts.id = post_likes.post_id 
                 WHERE posts.id = %s
                 GROUP BY posts.id"""
        cursor.execute(sql, (id,))
        row = cursor.fetchone()
        conn.commit()
        return jsonify(row)


@app.route('/posts/<int:post_id>/likes', methods=['POST'])
def like_post(post_id):
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        user_id = request.get_json().get('user_id')
        sql = """INSERT INTO post_likes(post_id, user_id) VALUES(%s, %s)"""
        cursor.execute(sql, (post_id, user_id))
        conn.commit()
        return jsonify({"message": "Like Added"})


@app.route('/posts/<int:post_id>/comments', methods=['POST'])
def add_comment_post(post_id):
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        user_id = request.get_json().get('user_id')
        content = request.get_json().get('content')
        now = datetime.now()
        formatted_datetime = now.strftime('%Y-%m-%d %H:%M:%S')
        sql = """INSERT INTO comments(post_id, user_id, content, created) VALUES(%s, %s, %s, %s)"""
        cursor.execute(sql, (post_id, user_id, content, formatted_datetime))
        conn.commit()
        return jsonify({"message": "Comment Added"})


@app.route('/posts/<int:post_id>/unlike', methods=['POST'])
def unlike_post(post_id):
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        user_id = request.get_json().get('user_id')
        sql = """DELETE FROM post_likes WHERE user_id = %s AND post_id = %s"""
        cursor.execute(sql, (user_id, post_id))
        conn.commit()
        return jsonify({"message": "Post Unliked"})


@app.route('/comments/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'DELETE':
        sql = """DELETE FROM comments WHERE id = %s"""
        cursor.execute(sql, (comment_id,))
        conn.commit()
        return jsonify({"message": "Comment Deleted"})


@app.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'DELETE':
        sql = """DELETE FROM posts WHERE id = %s"""
        cursor.execute(sql, (post_id,))
        conn.commit()
        return jsonify({"message": "Post Deleted"})


@app.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'GET':
        cursor.execute(
            "SELECT id, user_id, content, DATE_FORMAT(created, '%%M %%d') AS formatted_date FROM comments WHERE post_id = %s",
            (post_id,))
        comments = cursor.fetchall()
        return jsonify(comments)

if __name__ == '__main__':
    app.run(port=8000, debug=True)