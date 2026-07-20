import math
import os
import psycopg
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Create Database and Table
def init_db():
    conn = psycopg.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            title TEXT,
            content TEXT,
            location TEXT,
            image TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# View All Posts
@app.route("/posts", methods=["GET"])
def get_posts():

    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)

    offset = (page - 1) * limit

    conn = psycopg.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM posts")
    total_posts = cursor.fetchone()[0]

    total_pages = max(1, math.ceil(total_posts / limit))

    cursor.execute(
        """
        SELECT * FROM posts
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset)
    )

    rows = cursor.fetchall()

    conn.close()

    posts = []

    for row in rows:
        # Check if an image filename exists in the database row[4]
        image_filename = row[4]
        if image_filename:
            # Combines the current server domain with the static path
            full_image_url = f"{request.host_url}static/uploads/{image_filename}"
        else:
            full_image_url = None

        posts.append({
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "location": row[3],
            "image": full_image_url  # Sends the complete URL to the client
        })

    return jsonify({
        "meta": {
            "page": page,
            "limit": limit,
            "total_posts": total_posts,
            "total_pages": total_pages
        },
        "data": posts
    })


# Create New Post
@app.route("/posts", methods=["POST"])
def add_post():

    title = request.form["title"]
    content = request.form["content"]
    location = request.form["location"]

    if "image" not in request.files:
        return jsonify({"Message": "No image uploaded"}), 400

    image = request.files["image"]

    if image.filename == "":
        return jsonify({"message": "No image selected"}), 400

    if not allowed_file(image.filename):
        return jsonify({"message": "Only jpg, jpeg and png files allowed"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, image.filename)

    image.save(filepath)

    conn = psycopg.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute(
        """
    INSERT INTO posts
    (title, content, location, image )
    VALUES (%s, %s, %s, %s)
    RETURNING id
    """,
        (
            title,
            content,
            location,
            image.filename
        )

    )

    post_id = cursor.fetchone()[0]
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Post created sucessfully",
        "post": {
            "id": post_id,
            "title": title,
            "content": content,
            "location": location,
            "image": f"{request.host_url}static/uploads/{image.filename}"
        }
    }), 201


if __name__ == "__main__":
    app.run(debug=True)
