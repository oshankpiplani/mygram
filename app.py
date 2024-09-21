from flask import Flask, request, jsonify
import pymysql
from datetime import datetime
from flask_cors import CORS, cross_origin
import logging

app = Flask(__name__)
CORS(app, origins="*")

logging.getLogger('flask_cors').level = logging.DEBUG

def db_connection():
    conn = None
    try:
        conn = pymysql.connect(host='localhost',
                               database='mygram',
                               user='root',
                               password='Pepsi@123',
                               charset='utf8mb4',
                               cursorclass=pymysql.cursors.DictCursor)
    except pymysql.MySQLError as e:
        print(e)
    return conn

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

@app.route('/posts', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin()
def posts():
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'GET':
        userid = request.args.get('userid')
        sql = """SELECT title, DATE_FORMAT(created, '%%M %%d') AS formatted_date, LEFT(description, 30) AS short_description,id FROM posts WHERE user_id = %s"""
        cursor.execute(sql, (userid,))
        rows = cursor.fetchall()
        conn.commit()
        return jsonify(rows)
    
    if request.method == 'POST':
        data = request.get_json()
        title = data.get('title')
        description = data.get('description')
        userid = data.get('userId')
        now = datetime.now()
        formatted_datetime = now.strftime('%Y-%m-%d %H:%M:%S')
        sql = """INSERT INTO posts(title, description, created, user_id) VALUES(%s, %s, %s, %s)"""
        cursor.execute(sql, (title, description, formatted_datetime, userid))
        conn.commit()
        return jsonify({"message": "Post Added"})

@app.route('/posts/<int:id>', methods=['GET'])
def post_by_id(id):
    conn = db_connection()
    cursor = conn.cursor()
    if request.method == 'GET':
        sql = """SELECT posts.title,
                        posts.description,
                        posts.created,
                        COUNT(DISTINCT comments.id) AS num_comments,
                        COUNT(DISTINCT post_likes.id) AS num_likes
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
        cursor.execute("SELECT id, user_id, content,DATE_FORMAT(created, '%%M %%d') AS formatted_date FROM comments WHERE post_id = %s", (post_id,))
        comments = cursor.fetchall()
        return jsonify(comments)


if __name__ == '__main__':
    app.run(port=8000, debug=True)
