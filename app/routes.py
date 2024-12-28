from flask import Blueprint, request, render_template, jsonify

bp = Blueprint('main', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'txt'}


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file format, only .txt allowed'}), 400

    file_content = file.read().decode('utf-8')

    return jsonify({'filename': file.filename, 'content': file_content})
