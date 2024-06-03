from flask import Flask, request, send_file, render_template, jsonify
import socket
import base64
import cv2
import numpy as np
import time
import os
import threading

app = Flask(__name__)

# Dictionary to store the status of each image processing request
processing_status = {}

def send_request(filename, operation, host, port, request_id):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    print("Image is being processed .....")
    with open(filename, "rb") as f:
        img_data = f.read(8192)
        while img_data:
            client_socket.send(img_data)
            img_data = f.read(8192)

    message = b"IMAGE SENT"
    client_socket.send(message)

    message = client_socket.recv(8192)
    if message == b"IMAGE RECEIVED":
        print("Server received image safely")
        client_socket.send(f"{operation}".encode())

    message = client_socket.recv(8192).decode()
    print(message)

    client_socket.send(b"operation request is sent successfully, waiting for image to be processed")

    processed_img_bytes = b""
    while True:
        chunk = client_socket.recv(8192)
        if not chunk:
            break
        processed_img_bytes += chunk
        if b"DONE" in chunk:
            print("Processed image received at client")
            client_socket.send(b"CLIENT_DONE")
            break

    if not processed_img_bytes:
        print("Error: Did not receive any image data from server.")
        processing_status[request_id] = "error"
        return

    processed_img_bytes = processed_img_bytes[:-len(b"DONE")]

    img_array = np.frombuffer(processed_img_bytes, dtype=np.uint8)
    processed_img = cv2.imdecode(img_array, flags=cv2.IMREAD_COLOR)
    if processed_img is not None and processed_img.size > 0:
        timestamp = int(time.time())
        processed_filename = f"processed_image_{timestamp}.jpg"
        cv2.imwrite(processed_filename, processed_img)
        processing_status[request_id] = processed_filename
        print(f"Processed image saved as {processed_filename} successfully.")
    else:
        print("Error: Invalid image dimensions.")
        processing_status[request_id] = "error"

    client_socket.close()
    print("Socket closed.")

@app.route('/', methods=['GET'])
def index():
    html = """
    <html>
      <head>
        <title>Image Processing App</title>
        <style>
          body {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
          }
          .container {
            background-color: #f0f0f0;
            padding: 20px;
            border: 1px solid #ccc;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
          }
          .button {
            background-color: #4CAF50;
            color: #fff;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
          }
          .button:hover {
            background-color: #3e8e41;
          }
          .progress {
            width: 100%;
            background-color: #ccc;
          }
          .progress-bar {
            width: 0;
            height: 30px;
            background-color: #4CAF50;
          }
        </style>
        <script>
          function updateProgressBar(percentage) {
            var progressBar = document.getElementById("progress-bar");
            progressBar.style.width = percentage + "%";
          }

          function checkStatus(requestId) {
            fetch('/status/' + requestId)
              .then(response => response.json())
              .then(data => {
                if (data.status === "processing") {
                  updateProgressBar(50);
                  setTimeout(() => checkStatus(requestId), 1000);
                } else if (data.status === "complete") {
                  updateProgressBar(100);
                  document.getElementById("status").innerHTML = "Image processed successfully!";
                } else {
                  document.getElementById("status").innerHTML = "Error processing image.";
                }
              });
          }

          function processImage(event) {
            event.preventDefault();
            updateProgressBar(10);
            var form = document.getElementById("image-form");
            var formData = new FormData(form);
            fetch('/process_image', {
              method: 'POST',
              body: formData
            })
            .then(response => response.json())
            .then(data => {
              if (data.request_id) {
                checkStatus(data.request_id);
              }
            });
          }
        </script>
      </head>
      <body>
        <div class="container">
          <h1>Image Processing App</h1>
          <form id="image-form" onsubmit="processImage(event)">
            <label for="filename">Filename:</label>
            <input type="text" id="filename" name="filename"><br><br>
            <label for="operation">Operation:</label>
            <select id="operation" name="operation">
              <option value="grayscale">Grayscale</option>
              <option value="blur">Blur</option>
              <option value="edge_detection">Edge Detection</option>
              <option value="thresholding">Thresholding</option>
              <option value="histogram_equalization">Histogram Equalization</option>
              <option value="rotation_left">Rotate Left</option>
              <option value="rotation_right">Rotate Right</option>
              <option value="corner_detection">Corner Detection</option>
              <option value="deblurring">Deblurring</option>
            </select><br><br>
            <div id="scalingFields" style="display:none;">
              <label for="width">Width:</label>
              <input type="text" id="width" name="width"><br><br>
              <label for="height">Height:</label>
              <input type="text" id="height" name="height"><br><br>
            </div>
            <input type="submit" class="button" value="Process Image">
          </form>
          <div class="progress">
            <div id="progress-bar" class="progress-bar"></div>
          </div>
          <p id="status"></p>
          <p><a href="/download_processed_image">Download Processed Image</a></p>
        </div>
      </body>
    </html>
    """
    return html

@app.route('/process_image', methods=['POST'])
def process_image():
    filename = request.form['filename']
    operation = request.form['operation']
    host = '13.38.35.41'  # Replace with your EC2 instance's public IP address
    port = 10240  # Same port number used in the server code

    # Generate a unique request ID
    request_id = str(int(time.time()))
    processing_status[request_id] = "processing"

    # Start the image processing in a separate thread
    thread = threading.Thread(target=send_request, args=(filename, operation, host, port, request_id))
    thread.start()

    return jsonify(request_id=request_id)

@app.route('/status/<request_id>', methods=['GET'])
def status(request_id):
    status = processing_status.get(request_id, "unknown")
    if status.endswith(".jpg"):
        status = "complete"
    elif status == "error":
        status = "error"
    return jsonify(status=status)

@app.route('/download_processed_image', methods=['GET'])
def download_processed_image():
    timestamp = int(time.time())
    processed_filename = f"processed_image_{timestamp}.jpg"
    return send_file(processed_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

