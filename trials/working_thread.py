import threading
import queue
import uuid

import cv2
from flask import Flask, request, send_file
import os

# Task queue for image processing jobs
task_queue = queue.Queue()

# Image processing function
def process_image(image_path, operation):
    img = cv2.imread(image_path)

    if operation == "grayscale":
        processed_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif operation == "blur":
        processed_img = cv2.GaussianBlur(img, (5, 5), 0)
    elif operation == "edge_detection":
        processed_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_img = cv2.Canny(processed_img, 100, 200)  # Canny edge detection
    # Add more operations as needed

    processed_image_path = f"processed_{os.path.basename(image_path)}"
    cv2.imwrite(processed_image_path, processed_img)
    return processed_image_path

# Worker thread for processing tasks
class WorkerThread(threading.Thread):
    def __init__(self, task_queue):
        threading.Thread.__init__(self)
        self.task_queue = task_queue

    def run(self):
        while True:
            task = self.task_queue.get()
            image_path = task["image_path"]
            operation = task["operation"]
            result_path = process_image(image_path, operation)
            # ... handle result upload or further actions
            self.task_queue.task_done()

# Flask app for user interface and image upload
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def upload_and_process():
    if request.method == "POST":
        image_file = request.files["image"]
        operation = request.form["operation"]

        # Generate a unique filename
        filename = f"uploaded_image_{str(uuid.uuid4())}.jpg"
        # Assuming the image is a JPEG

        # Define the upload directory (create it if it doesn't exist)
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        # Save the image
        image_path = os.path.join(upload_dir, filename)
        image_file.save(image_path)

        # Add task to the queue
        task_queue.put({"image_path": image_path, "operation": operation})

        return "Image processing started..."

    return """
<!DOCTYPE html>
<html>
<head>
    <title>Image Processing</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f8f9fa;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 500px;
            margin: 50px auto;
            padding: 20px;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 20px;
        }
        form {
            text-align: center;
        }
        input[type="file"] {
            margin-bottom: 10px;
        }
        select {
            margin-bottom: 10px;
            padding: 5px;
            border-radius: 4px;
        }
        input[type="submit"] {
            background-color: #4CAF50;
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        input[type="submit"]:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Upload and Process Image</h1>
        <form method="post" enctype="multipart/form-data">
            <label for="image">Select an image:</label><br>
            <input type="file" name="image" id="image"><br><br>
            <label for="operation">Select an operation:</label><br>
            <select name="operation" id="operation">
                <option value="grayscale">Grayscale</option>
                <option value="blur">Blur</option>
                <option value="edge_detection">Edge Detection</option>
                <!-- Add more options here -->
            </select><br><br>
            <input type="submit" value="Process">
        </form>
    </div>
</body>
</html>
    """

@app.route("/processed_image/<filename>")
def processed_image(filename):
    processed_image_path = os.path.join("uploads", filename)
    return send_file(processed_image_path, mimetype="image/jpeg")

if __name__ == "__main__":
    # Start worker threads
    for i in range(4):  # Adjust number of threads as needed
        worker = WorkerThread(task_queue)
        worker.daemon = True
        worker.start()

    app.run(host="0.0.0.0")
