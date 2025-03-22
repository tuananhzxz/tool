from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
from PIL import Image
import shutil
from changeImage import convert_images
from cutmergeimage import ImageProcessor
from mergeWord import merge_word_documents
from renameImage import rename_files
import requests
from bs4 import BeautifulSoup
import io
import zipfile
import re
from flask_cors import CORS
from ocr_processor import process_folder

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max-limit

# Đảm bảo thư mục uploads tồn tại
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Thêm cấu hình cho Gemini API key
app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', '')

# Hàm xử lý lỗi chung
def handle_error(e):
    error_msg = str(e)
    if isinstance(e, requests.exceptions.RequestException):
        error_msg = "Lỗi kết nối: Không thể tải dữ liệu từ URL"
    elif isinstance(e, IOError):
        error_msg = "Lỗi đọc/ghi file"
    elif isinstance(e, Image.UnidentifiedImageError):
        error_msg = "File ảnh không hợp lệ hoặc bị hỏng"
    return jsonify({'error': error_msg})

@app.route('/')
def index():
    functions = {
        'changeImage': 'Chuyển đổi định dạng ảnh',
        'cutmergeimage': 'Cắt và ghép ảnh',
        'dowloaf': 'Tải ảnh từ web',
        'mergeWord': 'Gộp file Word',
        'renameImage': 'Đổi tên ảnh',
        'ocr': 'Nhận dạng chữ trong ảnh (OCR)'
    }
    return render_template('index.html', functions=functions)

@app.route('/function/<function_name>')
def function_page(function_name):
    titles = {
        'changeImage': 'Chuyển đổi định dạng ảnh',
        'cutmergeimage': 'Cắt và ghép ảnh',
        'dowloaf': 'Tải ảnh từ web',
        'mergeWord': 'Gộp file Word',
        'renameImage': 'Đổi tên ảnh',
        'ocr': 'Nhận dạng chữ trong ảnh (OCR)'
    }
    return render_template('function.html', 
                         function_name=function_name,
                         function_title=titles.get(function_name, 'Unknown Function'))

@app.route('/execute/changeImage', methods=['POST'])
def execute_change_image():
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'Không có file được tải lên'})
        
        files = request.files.getlist('files')
        target_format = request.form.get('target_format', 'webp')
        
        if not files or files[0].filename == '':
            return jsonify({'error': 'Không có file được chọn'})
            
        # Tạo thư mục tạm thời
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_convert')
        output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'output_convert')
        
        for dir_path in [temp_dir, output_dir]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            os.makedirs(dir_path)
            
        # Lưu và xử lý từng file
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(temp_dir, filename)
                file.save(file_path)
                
                # Xác định định dạng nguồn và chuyển đổi
                with Image.open(file_path) as img:
                    source_format = img.format
                    # Chuyển đổi và lưu với định dạng mới
                    output_path = os.path.join(output_dir, os.path.splitext(filename)[0] + '.' + target_format.lower())
                    if target_format.upper() == 'WEBP':
                        img.save(output_path, 'WEBP', quality=90)
                    elif target_format.upper() == 'JPEG':
                        if img.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            background.paste(img, mask=img.split()[-1])
                            background.save(output_path, 'JPEG', quality=95)
                        else:
                            img.save(output_path, 'JPEG', quality=95)
                    else:  # PNG
                        img.save(output_path, 'PNG')
        
        # Tạo file zip
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'converted_images.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_dir)
                    zipf.write(file_path, arcname)
        
        # Xóa thư mục tạm
        shutil.rmtree(temp_dir)
        shutil.rmtree(output_dir)
        
        return jsonify({
            'message': 'Chuyển đổi thành công!',
            'output_files': ['converted_images.zip']
        })
        
    except Exception as e:
        return handle_error(e)

@app.route('/execute/cutmergeimage', methods=['POST'])
def execute_cut_merge_image():
    if 'files' not in request.files:
        return jsonify({'error': 'Không có file được tải lên'})
    
    files = request.files.getlist('files')
    action = request.form.get('action')
    parts = int(request.form.get('parts', 2))
    width = request.form.get('width')
    height = request.form.get('height')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'Không có file được chọn'})
        
    # Tạo thư mục tạm thời
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_process')
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
        
    try:
        # Lưu các file
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(temp_dir, filename)
                file.save(file_path)
                
                # Resize ảnh nếu có yêu cầu
                if width or height:
                    with Image.open(file_path) as img:
                        new_width = int(width) if width else img.width
                        new_height = int(height) if height else img.height
                        resized = img.resize((new_width, new_height))
                        resized.save(file_path)
        
        processor = ImageProcessor(temp_dir)
        
        if action == 'split':
            processor.split_images(parts)
        else:  # merge
            processor.combine_images(parts)
        
        # Tạo file zip chứa kết quả
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_images.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Xóa thư mục tạm
        shutil.rmtree(temp_dir)
        
        return jsonify({
            'message': 'Xử lý thành công!',
            'output_files': ['processed_images.zip']
        })
        
    except Exception as e:
        return handle_error(e)

@app.route('/execute/dowloaf', methods=['POST'])
def execute_download():
    url = request.form.get('url')
    html_code = request.form.get('html_code')
    
    if not url and not html_code:
        return jsonify({'error': 'Vui lòng cung cấp URL hoặc mã HTML'})
    
    try:
        # Tạo thư mục tạm thời
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_download')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        if url:
            # Kiểm tra nếu là trang webtoon
            if 'newtoki' in url or 'webtoon' in url:
                # Tải trang web với bypass cloudflare
                session = requests.Session()
                response = session.get(url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Tìm danh sách chapter
                chapters = []
                if 'newtoki' in url:
                    chapter_links = soup.find_all('a', href=re.compile(r'/webtoon/\d+'))
                    for link in chapter_links:
                        chapters.append({
                            'title': link.text.strip(),
                            'url': 'https://newtoki.com' + link['href']
                        })
                elif 'webtoon' in url:
                    chapter_links = soup.find_all('a', href=re.compile(r'/episode/\d+'))
                    for link in chapter_links:
                        chapters.append({
                            'title': link.text.strip(),
                            'url': 'https://www.webtoons.com' + link['href']
                        })
                
                if chapters:
                    return jsonify({
                        'message': 'Đã tìm thấy danh sách chapter',
                        'chapters': chapters
                    })
            
            # Tải trang web
            session = requests.Session()
            response = session.get(url, headers=headers)
            html_content = response.text
        else:
            html_content = html_code
        
        # Phân tích HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Tìm tất cả thẻ img và source
        images = []
        for img in soup.find_all(['img', 'source']):
            src = img.get('src') or img.get('data-src') or img.get('srcset')
            if src:
                # Xử lý srcset
                if 'srcset' in img.attrs:
                    srcs = [s.strip().split()[0] for s in src.split(',')]
                    src = srcs[-1]  # Lấy ảnh có độ phân giải cao nhất
                
                # Chuẩn hóa URL
                if not src.startswith('http'):
                    if src.startswith('//'):
                        src = 'https:' + src
                    else:
                        src = 'https://' + src
                
                images.append({
                    'url': src,
                    'alt': img.get('alt', ''),
                    'preview': src
                })
        
        if not images:
            return jsonify({'error': 'Không tìm thấy ảnh nào'})
        
        return jsonify({
            'message': f'Đã tìm thấy {len(images)} ảnh',
            'images': images
        })
        
    except Exception as e:
        return handle_error(e)

@app.route('/execute/mergeWord', methods=['POST'])
def execute_merge_word():
    if 'files' not in request.files:
        return jsonify({'error': 'Không có file được tải lên'})
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'Không có file được chọn'})
    
    # Tạo thư mục tạm thời
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_word')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    try:
        # Lưu các file
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(temp_dir, filename)
                file.save(file_path)
        
        # Gộp file
        output_path = os.path.join(temp_dir, 'merged_document.docx')
        success = merge_word_documents(temp_dir, output_path)
        
        if success:
            # Tạo file zip chứa kết quả
            zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged_documents.zip')
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write(output_path, 'merged_document.docx')
            
            # Xóa thư mục tạm
            shutil.rmtree(temp_dir)
            
            return jsonify({
                'message': 'Gộp file thành công!',
                'output_files': ['merged_documents.zip']
            })
        else:
            return jsonify({'error': 'Không thể gộp các file'})
        
    except Exception as e:
        return handle_error(e)

@app.route('/execute/renameImage', methods=['POST'])
def execute_rename_image():
    if 'files' not in request.files:
        return jsonify({'error': 'Không có file được tải lên'})
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'Không có file được chọn'})
    
    # Tạo thư mục tạm thời
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_rename')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    try:
        # Lưu các file
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(temp_dir, filename)
                file.save(file_path)
        
        # Đổi tên file
        rename_files(temp_dir)
        
        # Tạo file zip chứa kết quả
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'renamed_images.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Xóa thư mục tạm
        shutil.rmtree(temp_dir)
        
        return jsonify({
            'message': 'Đổi tên file thành công!',
            'output_files': ['renamed_images.zip']
        })
        
    except Exception as e:
        return handle_error(e)

@app.route('/execute/ocr', methods=['POST'])
def execute_ocr():
    if 'files' not in request.files:
        return jsonify({'error': 'Không có file được tải lên'})
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'Không có file được chọn'})
    
    # Lấy các tham số bổ sung
    api_key = request.form.get('api_key', app.config['GEMINI_API_KEY'])
    genre = request.form.get('genre')  # Thể loại truyện
    target_langs = request.form.getlist('target_langs[]')  # Danh sách ngôn ngữ đích
    
    # Tạo thư mục tạm thời
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_ocr')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    try:
        # Lưu các file
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(temp_dir, filename)
                file.save(file_path)
        
        # Xử lý OCR với các tham số mới
        output_files = process_folder(temp_dir, api_key, genre, target_langs)
        
        # Tạo file zip chứa kết quả
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ocr_result.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Thêm các file Word kết quả cho từng ngôn ngữ
            for lang, files in output_files.items():
                for file in files:
                    arcname = os.path.basename(file)
                    zipf.write(file, arcname)
        
        # Xóa thư mục tạm
        shutil.rmtree(temp_dir)
        
        return jsonify({
            'message': 'Xử lý OCR thành công!',
            'output_files': ['ocr_result.zip'],
            'word_files': {
                lang: [os.path.basename(f) for f in files]
                for lang, files in output_files.items()
            }
        })
        
    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return handle_error(e)

@app.route('/execute/merge_ocr', methods=['POST'])
def execute_merge_ocr():
    if 'files' not in request.files:
        return jsonify({'error': 'Không có file được tải lên'})
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'Không có file được chọn'})
    
    # Tạo thư mục tạm thời
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_merge_ocr')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    try:
        # Lưu các file Word
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(temp_dir, filename)
                file.save(file_path)
        
        # Gộp các file Word
        output_path = os.path.join(temp_dir, 'merged_ocr.docx')
        success = merge_word_documents(temp_dir, output_path)
        
        if success:
            # Tạo file zip chứa kết quả
            zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged_ocr.zip')
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write(output_path, 'merged_ocr.docx')
            
            # Xóa thư mục tạm
            shutil.rmtree(temp_dir)
            
            return jsonify({
                'message': 'Gộp file thành công!',
                'output_files': ['merged_ocr.zip']
            })
        else:
            return jsonify({'error': 'Không thể gộp các file'})
        
    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return handle_error(e)

@app.route('/execute/download_images', methods=['POST'])
def download_selected_images():
    try:
        # Lấy danh sách URL ảnh đã chọn
        image_urls = request.json.get('image_urls', [])
        if not image_urls:
            return jsonify({'error': 'Không có ảnh nào được chọn'})
        
        # Tạo thư mục tạm thời
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_download')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # Tải các ảnh đã chọn
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        downloaded_files = []
        for i, url in enumerate(image_urls, 1):
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    img_name = f'image_{i}.jpg'
                    img_path = os.path.join(temp_dir, img_name)
                    
                    with open(img_path, 'wb') as f:
                        f.write(response.content)
                    downloaded_files.append(img_name)
            except Exception as e:
                print(f"Lỗi khi tải ảnh {url}: {str(e)}")
                continue
        
        if not downloaded_files:
            return jsonify({'error': 'Không thể tải xuống ảnh nào'})
        
        # Tạo file zip chứa kết quả
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'downloaded_images.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in downloaded_files:
                file_path = os.path.join(temp_dir, file)
                zipf.write(file_path, file)
        
        # Xóa thư mục tạm
        shutil.rmtree(temp_dir)
        
        return jsonify({
            'message': f'Đã tải xuống {len(downloaded_files)} ảnh!',
            'output_files': ['downloaded_images.zip']
        })
        
    except Exception as e:
        return handle_error(e)

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File không tồn tại'})
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return handle_error(e)

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File quá lớn. Kích thước tối đa là 16MB'}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Lỗi máy chủ nội bộ'}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Không tìm thấy trang'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
