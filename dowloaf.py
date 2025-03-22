import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urlparse
import time
import sys


def download_manga_images(url, output_folder='manga_images'):
    # Tạo thư mục đầu ra nếu chưa tồn tại
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Lấy tên truyện từ URL để đặt tên thư mục
    parsed_url = urlparse(url)
    manga_name = parsed_url.path.split('/')[1]
    chapter = re.search(r'chap-(\d+)', parsed_url.path)
    chapter_num = chapter.group(1) if chapter else "unknown_chapter"

    chapter_folder = os.path.join(output_folder, f"{manga_name}_chap_{chapter_num}")
    if not os.path.exists(chapter_folder):
        os.makedirs(chapter_folder)

    # Gửi request và lấy nội dung trang
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Tìm phần view-chapter chứa hình ảnh (dựa trên HTML mà bạn cung cấp)
        view_chapter_div = soup.find('div', id='view-chapter')
        if not view_chapter_div:
            # Thử tìm theo class nếu id không tồn tại
            view_chapter_div = soup.find('div', class_='view-chapter')

        if not view_chapter_div:
            print("Không tìm thấy phần nội dung truyện trong trang.")
            # Thử phương pháp khác - tìm tất cả thẻ div có class shadow-box
            view_chapter_div = soup.find('div', class_='shadow-box')

        if not view_chapter_div:
            print("Không thể xác định cấu trúc trang. Thử tìm tất cả hình ảnh...")
            img_tags = soup.find_all('img')
        else:
            img_tags = view_chapter_div.find_all('img')

        if not img_tags:
            print("Không tìm thấy hình ảnh nào trong chương truyện.")
            return

        print(f"Đã tìm thấy {len(img_tags)} hình ảnh.")

        # Lọc ra hình ảnh truyện (thường có thuộc tính alt chứa tên truyện hoặc URL gốc từ store)
        manga_images = []
        for img in img_tags:
            img_src = img.get('src')
            img_alt = img.get('alt', '')

            # Kiểm tra nếu là hình ảnh truyện (dựa vào URL hoặc alt text)
            if ((img_src and ('gianhangsach' in img_src)) or
                    (img_alt and manga_name.lower() in img_alt.lower())):
                manga_images.append(img)

        if not manga_images:
            print("Không tìm thấy hình ảnh truyện phù hợp, sử dụng tất cả hình ảnh tìm thấy.")
            manga_images = img_tags

        print(f"Chuẩn bị tải {len(manga_images)} hình ảnh truyện.")

        # Tải từng hình ảnh
        for i, img in enumerate(manga_images):
            img_url = img.get('src')
            if not img_url:
                continue

            try:
                img_response = requests.get(img_url, headers=headers)
                img_response.raise_for_status()

                # Lấy phần mở rộng của file từ URL
                file_extension = os.path.splitext(img_url)[1]
                if not file_extension:
                    file_extension = '.jpg'  # Mặc định là jpg nếu không tìm thấy phần mở rộng

                # Lưu file
                file_name = f"{i + 1:03d}{file_extension}"
                file_path = os.path.join(chapter_folder, file_name)

                with open(file_path, 'wb') as f:
                    f.write(img_response.content)

                print(f"Đã tải: {file_name} - từ {img_url}")

                # Tạm dừng ngắn để tránh gây tải cho server
                time.sleep(0.5)

            except Exception as e:
                print(f"Lỗi khi tải ảnh {img_url}: {e}")

        print(f"\nHoàn tất! Tất cả hình ảnh đã được lưu vào thư mục: {chapter_folder}")

    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")


def extract_image_urls_from_html(html_content):
    """Trích xuất URL hình ảnh từ đoạn HTML đã cung cấp"""
    soup = BeautifulSoup(html_content, 'html.parser')
    img_tags = soup.find_all('img')

    image_urls = []
    for img in img_tags:
        if img.get('src'):
            image_urls.append(img.get('src'))

    return image_urls


def download_images_from_urls(image_urls, manga_name="Ném Đá Xuống Hồ", chapter_num="1", output_folder='manga_images'):
    """Tải hình ảnh từ danh sách URL"""
    chapter_folder = os.path.join(output_folder, f"{manga_name}_chap_{chapter_num}")
    if not os.path.exists(chapter_folder):
        os.makedirs(chapter_folder)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print(f"Chuẩn bị tải {len(image_urls)} hình ảnh truyện.")

    for i, img_url in enumerate(image_urls):
        try:
            img_response = requests.get(img_url, headers=headers)
            img_response.raise_for_status()

            # Lấy phần mở rộng của file từ URL
            file_extension = os.path.splitext(img_url)[1]
            if not file_extension:
                file_extension = '.jpg'  # Mặc định là jpg nếu không tìm thấy phần mở rộng

            # Lưu file
            file_name = f"{i + 1:03d}{file_extension}"
            file_path = os.path.join(chapter_folder, file_name)

            with open(file_path, 'wb') as f:
                f.write(img_response.content)

            print(f"Đã tải: {file_name} - từ {img_url}")

            # Tạm dừng ngắn để tránh gây tải cho server
            time.sleep(0.5)

        except Exception as e:
            print(f"Lỗi khi tải ảnh {img_url}: {e}")

    print(f"\nHoàn tất! Tất cả hình ảnh đã được lưu vào thư mục: {chapter_folder}")


# Phương pháp mới để đọc HTML từ file
def read_html_from_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Lỗi khi đọc file: {e}")
        return None


# Phiên bản cải tiến: Tất cả sử dụng tham số dòng lệnh để tránh lỗi EOF
if __name__ == "__main__":
    print("=== Công cụ tải truyện tranh ===")

    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        print("Chọn chế độ:")
        print("1. Tải từ URL trang web")
        print("2. Tải từ đoạn HTML đã copy")
        print("3. Tải từ file HTML")
        mode = input("Nhập lựa chọn của bạn (1, 2 hoặc 3): ")

    if mode == "1":
        url = input("Nhập URL của chương truyện: ")
        output_folder = input("Nhập tên thư mục lưu trữ (Enter để dùng mặc định 'manga_images'): ") or "manga_images"
        download_manga_images(url, output_folder)

    elif mode == "2":
        print("Nhập HTML của trang truyện:")
        print("(Để kết thúc nhập, gõ 'END' trên một dòng riêng và nhấn Enter)")

        html_content = []
        while True:
            try:
                line = input()
                if line.strip() == 'END':
                    break
                html_content.append(line)
            except KeyboardInterrupt:
                print("\nĐã hủy nhập.")
                sys.exit(0)

        html_content = '\n'.join(html_content)

        if not html_content:
            print("Không có HTML nào được nhập!")
            sys.exit(1)

        # Các thông số khác
        manga_name = input("Nhập tên truyện (Enter để dùng 'Ném Đá Xuống Hồ'): ") or "Ném Đá Xuống Hồ"
        chapter_num = input("Nhập số chương (Enter để dùng '1'): ") or "1"
        output_folder = input("Nhập thư mục lưu trữ (Enter để dùng 'manga_images'): ") or "manga_images"

        image_urls = extract_image_urls_from_html(html_content)
        if image_urls:
            print(f"Đã tìm thấy {len(image_urls)} hình ảnh.")
            download_images_from_urls(image_urls, manga_name, chapter_num, output_folder)
        else:
            print("Không tìm thấy URL hình ảnh nào trong đoạn HTML đã cung cấp.")

    elif mode == "3":
        html_file = input("Nhập đường dẫn đến file HTML: ")
        html_content = read_html_from_file(html_file)

        if not html_content:
            print("Không thể đọc file HTML!")
            sys.exit(1)

        manga_name = input("Nhập tên truyện (Enter để dùng 'Ném Đá Xuống Hồ'): ") or "Ném Đá Xuống Hồ"
        chapter_num = input("Nhập số chương (Enter để dùng '1'): ") or "1"
        output_folder = input("Nhập tên thư mục lưu trữ (Enter để dùng 'manga_images'): ") or "manga_images"

        image_urls = extract_image_urls_from_html(html_content)
        if image_urls:
            download_images_from_urls(image_urls, manga_name, chapter_num, output_folder)
        else:
            print("Không tìm thấy URL hình ảnh nào trong file HTML đã cung cấp.")

    else:
        print("Lựa chọn không hợp lệ!")