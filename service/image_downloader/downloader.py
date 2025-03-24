import os
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from PIL import Image
import io
import json
from concurrent.futures import ThreadPoolExecutor
from .sources import SourceConfig

class ImageDownloader:
    def __init__(self):
        self.source_config = SourceConfig()
        self.session = requests.Session()
        self.max_retries = 3
        self.max_workers = 5  # Số lượng thread tải đồng thời
        
    def is_valid_image_url(self, url):
        """Kiểm tra URL có phải là ảnh hợp lệ không"""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and bool(parsed.scheme)
        except:
            return False

    def is_valid_image_content(self, content):
        """Kiểm tra nội dung có phải là ảnh hợp lệ không"""
        try:
            Image.open(io.BytesIO(content))
            return True
        except:
            return False

    def get_random_user_agent(self):
        """Tạo User-Agent ngẫu nhiên"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
        return random.choice(user_agents)

    def get_headers(self, url):
        """Tạo headers phù hợp cho request"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Headers cơ bản
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Xử lý các domain đặc biệt
        if 'kcgsbok.com' in domain:
            headers.update({
                'Referer': 'https://kcgsbok.com/',
                'Origin': 'https://kcgsbok.com',
                'Host': parsed_url.netloc
            })
        elif 'twmanga.com' in domain:
            headers.update({
                'Referer': 'https://twmanga.com/',
                'Origin': 'https://twmanga.com',
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
        else:
            # Nếu không phải các domain đặc biệt, sử dụng domain gốc
            headers.update({
                'Referer': f'https://{domain}/',
                'Origin': f'https://{domain}',
                'Host': parsed_url.netloc
            })
        
        return headers

    def download_image(self, url, save_path, index):
        """Tải một ảnh với retry và xử lý lỗi"""
        max_retries = 3
        for retry in range(max_retries):
            try:
                # Thêm delay ngẫu nhiên giữa các lần thử
                if retry > 0:
                    time.sleep(random.uniform(2, 5))
                
                headers = self.get_headers(url)
                print(f"Tải ảnh {index} với headers: {headers}")
                
                response = self.session.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    if not self.is_valid_image_content(response.content):
                        return False, "File không phải là ảnh hợp lệ"
                    
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    return True, save_path
                    
                elif response.status_code == 403:  # Forbidden
                    if retry < max_retries - 1:
                        # Thử thay đổi User-Agent và Referer
                        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        # Thay đổi Referer nếu cần
                        if 'Referer' in headers:
                            headers['Referer'] = headers['Referer'].replace('http://', 'https://')
                        time.sleep(random.uniform(3, 6))
                    else:
                        return False, f"Lỗi 403 Forbidden sau {max_retries} lần thử"
                        
                else:
                    return False, f"Lỗi HTTP {response.status_code}"
                    
            except requests.exceptions.Timeout:
                if retry == max_retries - 1:
                    return False, "Timeout khi tải ảnh"
                time.sleep(random.uniform(3, 6))
                
            except requests.exceptions.RequestException as e:
                if retry == max_retries - 1:
                    return False, f"Lỗi khi tải ảnh: {str(e)}"
                time.sleep(random.uniform(3, 6))
                
        return False, "Đã hết số lần thử"

    def crawl_images(self, url):
        """Crawl tất cả ảnh từ trang web"""
        try:
            print(f"Bắt đầu crawl URL: {url}")
            headers = self.source_config.get_headers(url)
            print(f"Headers đã được tạo: {headers}")
            
            response = self.session.get(url, headers=headers, timeout=10)
            print(f"Status code: {response.status_code}")
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            print(f"Đã parse HTML thành công")
            image_urls = []
            
            # Tìm ảnh trong các thẻ img
            img_tags = soup.find_all('img')
            print(f"Số lượng thẻ img tìm thấy: {len(img_tags)}")
            
            for img in img_tags:
                # Kiểm tra các thuộc tính chứa URL ảnh
                for attr in ['data-url', 'data-src', 'data-original', 'data-lazy-src', 'src']:
                    src = img.get(attr, '')
                    if src:
                        print(f"Tìm thấy thuộc tính {attr}: {src}")
                        # Chuyển đổi URL tương đối thành URL tuyệt đối
                        if not src.startswith(('http://', 'https://')):
                            src = urljoin(url, src)
                            print(f"URL đã được chuyển đổi: {src}")
                        
                        # Loại bỏ các URL thumbnail và ảnh không liên quan
                        if any(x in src.lower() for x in ['type=f218_218', 'type=w160', 'type=w210', 'type=q90', 'type=a92', 'thumb_', 'thumbnail', 'bg_transparency']):
                            continue
                            
                        # Kiểm tra xem URL có phải là ảnh không
                        if any(src.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                            image_urls.append(src)
                            print(f"Thêm ảnh vào danh sách: {src}")
            
            # Tìm ảnh trong các thẻ div có class chứa từ khóa liên quan đến ảnh
            div_tags = soup.find_all('div', class_=lambda x: x and any(keyword in x.lower() for keyword in ['image', 'img', 'photo', 'picture', 'chapter', 'comic']))
            print(f"Số lượng thẻ div liên quan đến ảnh: {len(div_tags)}")
            
            for div in div_tags:
                # Tìm ảnh trong background-image
                style = div.get('style', '')
                if 'background-image' in style:
                    print(f"Tìm thấy background-image trong style: {style}")
                    # Trích xuất URL từ background-image
                    import re
                    urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
                    for src in urls:
                        if not src.startswith(('http://', 'https://')):
                            src = urljoin(url, src)
                        # Loại bỏ các URL thumbnail
                        if any(x in src.lower() for x in ['type=f218_218', 'type=w160', 'type=w210', 'type=q90', 'type=a92', 'thumb_', 'thumbnail']):
                            continue
                        if any(src.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                            image_urls.append(src)
                            print(f"Thêm ảnh từ background: {src}")
            
            # Tìm ảnh trong các thẻ a có href chứa URL ảnh
            a_tags = soup.find_all('a', href=lambda x: x and any(x.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']))
            for a in a_tags:
                src = a.get('href', '')
                if not src.startswith(('http://', 'https://')):
                    src = urljoin(url, src)
                # Loại bỏ các URL thumbnail
                if any(x in src.lower() for x in ['type=f218_218', 'type=w160', 'type=w210', 'type=q90', 'type=a92', 'thumb_', 'thumbnail']):
                    continue
                image_urls.append(src)
                print(f"Thêm ảnh từ thẻ a: {src}")
            
            # Loại bỏ các URL trùng lặp
            image_urls = list(dict.fromkeys(image_urls))
            
            print(f"Tổng số ảnh tìm thấy: {len(image_urls)}")
            if not image_urls:
                print("Không tìm thấy ảnh nào phù hợp")
                return []
                
            return image_urls
            
        except Exception as e:
            print(f"Lỗi chi tiết khi crawl ảnh: {str(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            return []

    def download_images_parallel(self, image_urls, temp_dir):
        """Tải nhiều ảnh song song"""
        downloaded_files = []
        failed_urls = []
        
        def download_task(args):
            url, index = args
            # Tạo tên file với số thứ tự
            img_name = f'image_{index:03d}.jpg'
            save_path = os.path.join(temp_dir, img_name)
            success, result = self.download_image(url, save_path, index)
            return success, result, url
            
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(download_task, (url, i+1)) 
                      for i, url in enumerate(image_urls)]
            
            for future in futures:
                success, result, url = future.result()
                if success:
                    downloaded_files.append(result)
                else:
                    failed_urls.append(f"{url}: {result}")
                    
        return downloaded_files, failed_urls

    def download_chapter(self, url, output_dir):
        """Tải toàn bộ chapter"""
        try:
            # Tạo thư mục output nếu chưa tồn tại
            os.makedirs(output_dir, exist_ok=True)
            
            # Crawl tất cả ảnh từ trang web
            image_urls = self.crawl_images(url)
            if not image_urls:
                return False, "Không tìm thấy ảnh nào trong trang web"
            
            # Tải ảnh song song
            downloaded_files, failed_urls = self.download_images_parallel(image_urls, output_dir)
            
            if not downloaded_files:
                return False, "Không thể tải xuống ảnh nào"
            
            # Tạo file thông tin
            info = {
                'total_images': len(image_urls),
                'downloaded_count': len(downloaded_files),
                'failed_count': len(failed_urls),
                'failed_urls': failed_urls,
                'source_url': url,
                'download_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(os.path.join(output_dir, 'info.json'), 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            
            return True, {
                'message': f'Đã tải xuống {len(downloaded_files)} ảnh!',
                'success_count': len(downloaded_files),
                'failed_count': len(failed_urls),
                'failed_urls': failed_urls
            }
            
        except Exception as e:
            return False, str(e) 