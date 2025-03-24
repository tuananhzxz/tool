import os
import shutil
import zipfile
from flask import current_app, jsonify, request
import requests
from urllib.parse import urlparse, urljoin
from PIL import Image
import io
import time
import random
from bs4 import BeautifulSoup
from .image_downloader import ImageDownloader

def is_valid_image_url(url):
    """Kiểm tra URL có phải là ảnh hợp lệ không"""
    try:
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)
    except:
        return False

def is_valid_image_content(content):
    """Kiểm tra nội dung có phải là ảnh hợp lệ không"""
    try:
        Image.open(io.BytesIO(content))
        return True
    except:
        return False

def get_random_user_agent():
    """Tạo User-Agent ngẫu nhiên"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
    ]
    return random.choice(user_agents)

def get_headers(url):
    """Tạo headers phù hợp cho request"""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    
    # Headers cơ bản
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # Xử lý các domain đặc biệt
    if 'webtoon-phinf.pstatic.net' in domain:
        headers.update({
            'Referer': 'https://comic.naver.com/',
            'Origin': 'https://comic.naver.com',
            'Host': parsed_url.netloc,
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site'
        })
    elif 'webtoon' in domain:
        headers.update({
            'Referer': 'https://comic.naver.com/',
            'Origin': 'https://comic.naver.com',
            'Host': parsed_url.netloc,
            'Accept-Encoding': 'gzip, deflate, br'
        })
    elif 'manga' in domain:
        headers.update({
            'Referer': 'https://manga.bilibili.com/',
            'Origin': 'https://manga.bilibili.com',
            'Host': parsed_url.netloc
        })
    elif 'nettruyen' in domain:
        headers.update({
            'Referer': 'https://nettruyen.com/',
            'Origin': 'https://nettruyen.com',
            'Host': parsed_url.netloc
        })
    elif 'truyenqq' in domain:
        headers.update({
            'Referer': 'https://truyenqq.com/',
            'Origin': 'https://truyenqq.com',
            'Host': parsed_url.netloc
        })
    elif 'truyen86' in domain:
        headers.update({
            'Referer': 'https://truyen86.com/',
            'Origin': 'https://truyen86.com',
            'Host': parsed_url.netloc
        })
    else:
        # Nếu không phải các domain đặc biệt, sử dụng domain gốc
        headers.update({
            'Referer': f'https://{domain}/',
            'Origin': f'https://{domain}',
            'Host': parsed_url.netloc
        })
    
    return headers

def download_image(url, headers, temp_dir, index):
    """Tải một ảnh với retry và xử lý lỗi"""
    max_retries = 3
    for retry in range(max_retries):
        try:
            # Thêm delay ngẫu nhiên giữa các lần thử
            if retry > 0:
                time.sleep(random.uniform(1, 3))
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                if not is_valid_image_content(response.content):
                    return False, "File không phải là ảnh hợp lệ"
                
                img_name = f'image_{index}_{int(time.time())}.jpg'
                img_path = os.path.join(temp_dir, img_name)
                
                with open(img_path, 'wb') as f:
                    f.write(response.content)
                return True, img_name
                
            elif response.status_code == 403:  # Forbidden
                if retry < max_retries - 1:
                    # Thử thay đổi User-Agent và Referer
                    headers['User-Agent'] = get_random_user_agent()
                    # Thay đổi Referer nếu cần
                    if 'Referer' in headers:
                        headers['Referer'] = headers['Referer'].replace('http://', 'https://')
                    time.sleep(random.uniform(2, 4))
                else:
                    return False, f"Lỗi 403 Forbidden sau {max_retries} lần thử"
                    
            else:
                return False, f"Lỗi HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            if retry == max_retries - 1:
                return False, "Timeout khi tải ảnh"
            time.sleep(random.uniform(2, 4))
            
        except requests.exceptions.RequestException as e:
            if retry == max_retries - 1:
                return False, f"Lỗi khi tải ảnh: {str(e)}"
            time.sleep(random.uniform(2, 4))
            
    return False, "Đã hết số lần thử"

def crawl_images(url):
    """Crawl tất cả ảnh từ trang web"""
    try:
        headers = get_headers(url)
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        image_urls = []
        
        # Tìm tất cả thẻ img
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if not src:
                continue
                
            # Chuyển đổi URL tương đối thành URL tuyệt đối
            if not src.startswith(('http://', 'https://')):
                src = urljoin(url, src)
                
            # Kiểm tra xem URL có phải là ảnh không
            if any(src.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                image_urls.append(src)
                
        return image_urls
    except Exception as e:
        print(f"Error crawling images: {str(e)}")
        return []

def download_selected_images():
    try:
        # Lấy URL trang web
        base_url = request.json.get('base_url', '')
        print(f"Received base URL: {base_url}")  # Debug log
        
        if not base_url:
            return jsonify({'error': 'Vui lòng nhập URL trang web'})
        
        # Tạo thư mục tạm thời
        temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_download')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # Khởi tạo downloader và tải ảnh
        downloader = ImageDownloader()
        success, result = downloader.download_chapter(base_url, temp_dir)
        
        if not success:
            return jsonify({'error': result})
        
        # Tạo file zip chứa kết quả
        zip_filename = 'downloaded_images.zip'
        zip_path = os.path.join(current_app.config['UPLOAD_FOLDER'], zip_filename)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Xóa thư mục tạm
        shutil.rmtree(temp_dir)
        
        # Add output_files to the result
        result_with_files = result.copy() if isinstance(result, dict) else {}
        result_with_files.update({
            'message': f'Đã tải xuống {result.get("success_count", 0)} ảnh!',
            'output_files': [zip_filename]  # Add this line
        })
        
        # Trả về kết quả
        return jsonify(result_with_files)
        
    except Exception as e:
        print(f"General error in download_selected_images: {str(e)}")  # Debug log
        return jsonify({'error': str(e)})