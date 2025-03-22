import time
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
from speechbubble import SpeechBubbleProcessor
from docx import Document
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='public')
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max-limit

# Đảm bảo thư mục uploads tồn tại
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


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
    templates = {
        'changeImage': 'functions/changeimage.html',
        'cutmergeimage': 'functions/cutmergeimage.html',
        'dowloaf': 'functions/dowloaf.html',
        'mergeWord': 'functions/mergeword.html',
        'renameImage': 'functions/renameimage.html',
        'ocr': 'functions/ocr.html',
        'translate': 'functions/translate.html',
        'remove_speech_bubbles': 'functions/speechbubble.html'
    }
    
    if function_name not in templates:
        return jsonify({'error': 'Chức năng không tồn tại'}), 404
        
    return render_template(templates[function_name])

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
    try:
        files = request.files.getlist('files')
        api_key = request.form.get('api_key')
        mode = request.form.get('mode', 'ocr')  # Thêm mode để phân biệt OCR và dịch
        genres = request.form.getlist('genres[]')  # Lấy danh sách thể loại
        styles = request.form.getlist('styles[]')  # Lấy danh sách phong cách
        
        if not files or not api_key:
            return jsonify({'error': 'Vui lòng cung cấp file và API key'})
        
        # Khởi tạo client Gemini với API key
        client = genai.Client(api_key=api_key)
        model = client.models
        
        # Tạo một tài liệu Word mới
        doc = Document()
        doc.add_heading('Cám ơn đã sử dụng tôi iu bạn có thể mua ủng hộ ly cafe để web phát triển hơn...', 0)
        
        # Thêm thông tin về thể loại và phong cách
        if genres or styles:
            doc.add_paragraph('=== Thông tin truyện ===')
            if genres:
                doc.add_paragraph('Thể loại: ' + ', '.join(genres))
            if styles:
                doc.add_paragraph('Phong cách: ' + ', '.join(styles))
            doc.add_paragraph('---')
        
        extracted_texts = []
        
        # Xử lý từng file
        for file in files:
            if not file.filename:
                continue
                
            # Kiểm tra định dạng file
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext in ['.docx', '.doc']:
                # Xử lý file Word
                docx_doc = Document(file)
                text = ''
                for para in docx_doc.paragraphs:
                    text += para.text + '\n'
                
                if text.strip():
                    extracted_texts.append({
                        'filename': file.filename,
                        'text': text
                    })
                    
                    if mode == 'translate':
                        # Dịch văn bản
                        target_langs = request.form.getlist('target_langs[]')
                        for lang in target_langs:
                            # Thêm thông tin về thể loại và phong cách vào prompt
                            prompt = f"""
                                Hãy dịch đoạn văn bản sau sang {getLangName(lang)}.
                                Thể loại: {', '.join(genres) if genres else 'Không xác định'}
                                Phong cách: {', '.join(styles) if styles else 'Không xác định'}
                                
                                Văn bản cần dịch:
                                {text}
                            """
                            
                            response = model.generate_content(
                                model="gemini-2.0-flash",
                                contents=prompt,
                                config={"temperature": 0.4}
                            )
                            
                            if response.text:
                                doc.add_paragraph(f"=== {getLangName(lang)} ===")
                                doc.add_paragraph(response.text)
                                doc.add_paragraph('---')
                    else:
                        # OCR mode
                        doc.add_paragraph(text)
                        doc.add_paragraph('---')
                        
            else:
                # Xử lý file ảnh
                image_bytes = file.read()
                
                if mode == 'translate':
                    prompt = f"""
                        Hãy dịch tất cả các đoạn văn bản trong các bóng thoại của ảnh truyện tranh này.
                        Thể loại: {', '.join(genres) if genres else 'Không xác định'}
                        Phong cách: {', '.join(styles) if styles else 'Không xác định'}
                        
                        Chỉ trả về nội dung văn bản đã dịch, không cần giải thích thêm.
                    """
                else:
                    prompt = """
                        Hãy nhận dạng và liệt kê tất cả các đoạn văn bản trong các bóng thoại của ảnh truyện tranh này.
                        Mỗi bóng thoại sẽ được đánh số thứ tự và nội dung của nó.
                        Chỉ trả về nội dung văn bản, không cần giải thích thêm.
                    """
                
                # Gửi yêu cầu đến Gemini API
                response = model.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": image_bytes}}
                    ],
                    config={"temperature": 0.4}
                )
                
                # Lấy văn bản được nhận dạng
                extracted_text = response.text
                
                if extracted_text:
                    extracted_texts.append({
                        'filename': file.filename,
                        'text': extracted_text
                    })
                    
                    if mode == 'translate':
                        # Dịch văn bản
                        target_langs = request.form.getlist('target_langs[]')
                        for lang in target_langs:
                            prompt = f"""
                                Hãy dịch đoạn văn bản sau sang {getLangName(lang)}.
                                Thể loại: {', '.join(genres) if genres else 'Không xác định'}
                                Phong cách: {', '.join(styles) if styles else 'Không xác định'}
                                
                                Văn bản cần dịch:
                                {extracted_text}
                            """
                            
                            response = model.generate_content(
                                model="gemini-2.0-flash",
                                contents=prompt,
                                config={"temperature": 0.4}
                            )
                            
                            if response.text:
                                doc.add_paragraph(f"=== {getLangName(lang)} ===")
                                doc.add_paragraph(response.text)
                                doc.add_paragraph('---')
                    else:
                        # OCR mode
                        doc.add_paragraph(extracted_text)
                        doc.add_paragraph('---')
        
        if not extracted_texts:
            return jsonify({'error': 'Không tìm thấy văn bản nào để xử lý'})
        
        # Lưu tài liệu
        output_filename = f'VBCĐ_{int(time.time())}.docx'
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        doc.save(output_path)
        
        return jsonify({
            'success': True,
            'word_files': {'all': [output_filename]},
            'extracted_texts': extracted_texts
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

# Hàm chuyển đổi mã ngôn ngữ thành tên
def getLangName(code):
    langs = {
        'vie': 'Tiếng Việt',
        'eng': 'Tiếng Anh',
        'jpn': 'Tiếng Nhật',
        'kor': 'Tiếng Hàn'
    }
    return langs.get(code, code)

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

@app.route('/remove_speech_bubbles', methods=['GET', 'POST'])
def process_speech_bubbles():
    if request.method == 'GET':
        return render_template('functions/speechbubble.html')
    
    try:
        # Kiểm tra file upload
        if 'files' not in request.files:
            return jsonify({'error': 'Không tìm thấy file nào được tải lên'}), 400
            
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({'error': 'Không có file nào được chọn'}), 400
            
        # Lấy API key từ form hoặc sử dụng API key mặc định
        api_key = request.form.get('api_key', app.config['GEMINI_API_KEY'])
        
        # Cấu hình API key mới nếu có
        if api_key != app.config['GEMINI_API_KEY']:
            genai.Client(api_key=api_key)
            
        # Tạo thư mục tạm thời
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        # Xóa các file cũ trong thư mục tạm
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
            
        # Lưu các file upload
        for file in files:
            if file and allowed_file(file.filename):
                file.save(os.path.join(temp_dir, file.filename))
                
        # Xử lý ảnh
        processor = SpeechBubbleProcessor(api_key)
        output_dir = processor.process_folder(temp_dir)
        
        # Tạo file zip
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_images.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    zipf.write(os.path.join(root, file), file)
                    
        return jsonify({
            'success': True,
            'message': 'Xử lý ảnh thành công',
            'download_url': url_for('download_file', filename='processed_images.zip', _external=True)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/changeImage')
def change_image():
    return render_template('functions/changeimage.html')

@app.route('/cutmergeimage')
def cut_merge_image():
    return render_template('functions/cutmergeimage.html')

@app.route('/dowloaf')
def download_image():
    return render_template('functions/dowloaf.html')

@app.route('/mergeword')
def merge_word():
    return render_template('functions/mergeword.html')

@app.route('/renameimage')
def rename_image():
    return render_template('functions/renameimage.html')

@app.route('/ocr')
def ocr():
    return render_template('functions/ocr.html')

@app.route('/translate')
def translate():
    return render_template('functions/translate.html')

@app.route('/remove_speech_bubbles')
def remove_speech_bubbles():
    return render_template('functions/speechbubble.html')

@app.route('/test_api_key', methods=['POST'])
def test_api_key():
    try:
        data = request.json
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'API key không được cung cấp'})
        
        client = genai.Client(api_key=api_key)
        
        # Tạo một tin nhắn đơn giản để kiểm tra API key
        response = client.models.generate_content(
            model="gemini-2.0-flash", contents="Explain how AI works in a few words"
        )
        
        return jsonify({'success': True, 'message': 'API key hợp lệ'})
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
