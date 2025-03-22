import os
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class ChapterUploader:
    def __init__(self, website_url, username, password, base_folder, direct_url):
        self.website_url = website_url
        self.username = username
        self.password = password
        self.base_folder = base_folder
        self.direct_url = direct_url
        self.driver = None

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        self.driver = webdriver.Chrome(options=options)

    def login(self):
        self.driver.get(self.website_url)
        try:
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "txtUserName"))
            )
            password_input = self.driver.find_element(By.NAME, "txtPassword")
            login_button = self.driver.find_element(By.CSS_SELECTOR, ".btn.login-btn")

            username_input.send_keys(self.username)
            password_input.send_keys(self.password)
            login_button.click()

            # Truy cập trực tiếp vào URL thay vì tìm kiếm
            self.driver.get(self.direct_url)

            # Đợi trang tải xong
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "ctl12_btnThemChuong"))
            )

            return True
        except TimeoutException:
            print("Không thể đăng nhập hoặc truy cập trang. Kiểm tra lại thông tin.")
            return False

    def sort_image_files(self, files):
        """
        Hàm sắp xếp các file ảnh theo thứ tự XX_YY
        """

        def extract_numbers(filename):
            # Tách phần số từ tên file (ví dụ: '01_15.jpg' -> [1, 15])
            base = os.path.splitext(filename)[0]  # bỏ đuôi file
            parts = base.split('_')
            if len(parts) == 2:
                try:
                    return [int(parts[0]), int(parts[1])]
                except ValueError:
                    return [0, 0]
            return [0, 0]

        return sorted(files, key=extract_numbers)

    def extract_chapter_number(self, folder_name):
        """
        Trích xuất số chương từ tên thư mục có định dạng đặc biệt
        """
        # Pattern cho định dạng "Hồi Quy Trở Lại Thành Kẻ Vô Dụng - Hồi Quy Vô Giá Trị Chap 1 Next Chap 2 Tiếng Việt"
        chap_pattern = re.search(r'Chap\s*(\d+)', folder_name, re.IGNORECASE)
        if chap_pattern:
            return chap_pattern.group(1)

        # Pattern cũ
        old_pattern = re.search(r'chương\s*(\d+)', folder_name, re.IGNORECASE)
        if old_pattern:
            return old_pattern.group(1)

        # Không tìm thấy pattern nào
        return None

    def prepare_chapter(self, chapter_folder):
        try:
            self.driver.execute_script("window.open('');")  # Mở tab mới
            self.driver.switch_to.window(self.driver.window_handles[-1])  # Chuyển sang tab mới
            self.driver.get(self.direct_url)  # Truy cập trực tiếp vào trang cần upload

            # Lấy số chương từ tên thư mục với định dạng mới
            chapter_num = self.extract_chapter_number(chapter_folder)
            if not chapter_num:
                raise Exception(f"Không tìm thấy số chương trong thư mục: {chapter_folder}")

            # Thực hiện các bước thêm chương và tải ảnh
            a_click_add = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "ctl12_btnThemChuong"))
            )
            a_click_add.click()

            option_check = self.driver.find_element(By.ID, "ctl12_chkthuphi")
            option_check.click()

            input_stt = self.driver.find_element(By.NAME, "ctl12$txtSTT")
            input_title = self.driver.find_element(By.NAME, "ctl12$txtTitle")

            input_stt.clear()
            input_title.clear()

            # Đặt STT và Title là số chương
            input_stt.send_keys(chapter_num)
            input_title.send_keys(chapter_num)

            chapter_path = os.path.join(self.base_folder, chapter_folder)
            print(f"Đang tìm ảnh trong thư mục: {chapter_path}")

            if not os.path.exists(chapter_path):
                raise Exception(f"Không tìm thấy thư mục: {chapter_path}")

            # Sắp xếp và tải ảnh
            images = [f for f in os.listdir(chapter_path) if f.endswith(('.jpg', '.png', '.jpeg'))]
            images = self.sort_image_files(images)

            if not images:
                raise Exception(f"Không tìm thấy ảnh trong thư mục: {chapter_path}")

            print(f"Tìm thấy {len(images)} ảnh để upload")
            for idx, img in enumerate(images, 1):
                print(f"Uploading {idx}/{len(images)}: {img}")
                file_path = os.path.join(chapter_path, img)
                file_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                )
                file_input.send_keys(file_path)

            print(f"Đã upload tất cả ảnh cho chapter {chapter_num} trên tab này.")
            print(f"Chuyển sang tab khác để upload chapter tiếp theo.")

            return True

        except Exception as e:
            print(f"Lỗi khi chuẩn bị chapter {chapter_folder}: {str(e)}")
            return False

    def batch_upload(self):
        self.setup_driver()
        if not self.login():
            return

        # Lọc thư mục dựa trên các pattern khác nhau
        chapter_folders = []
        for d in os.listdir(self.base_folder):
            folder_path = os.path.join(self.base_folder, d)
            if not os.path.isdir(folder_path):
                continue

            # Kiểm tra cả hai pattern
            if re.search(r'Chap\s*\d+', d, re.IGNORECASE) or re.search(r'chương\s*\d+', d, re.IGNORECASE):
                chapter_folders.append(d)

        if not chapter_folders:
            print("Không tìm thấy thư mục chương nào.")
            return

        # Sắp xếp thư mục theo số chương
        def get_chapter_num(folder_name):
            chap_match = re.search(r'Chap\s*(\d+)', folder_name, re.IGNORECASE)
            if chap_match:
                return int(chap_match.group(1))

            old_match = re.search(r'chương\s*(\d+)', folder_name, re.IGNORECASE)
            if old_match:
                return int(old_match.group(1))

            return 0

        chapter_folders = sorted(chapter_folders, key=get_chapter_num)

        print(f"Tìm thấy {len(chapter_folders)} thư mục chương để upload.")
        for folder in chapter_folders:
            print(f" - {folder} (Chương {get_chapter_num(folder)})")

        for chapter_folder in chapter_folders:
            print(f"\nĐang chuẩn bị upload {chapter_folder}")
            success = self.prepare_chapter(chapter_folder)
            if not success:
                print(f"Thất bại khi upload {chapter_folder}!")
                if input("Bạn có muốn tiếp tục với chapter tiếp theo? (y/n): ").lower() != 'y':
                    break
            time.sleep(1)

        print("Tất cả các tab đã được mở. Vui lòng nhấn Submit trên từng tab để hoàn tất.")
        self.driver.switch_to.window(self.driver.window_handles[0])  # Quay lại tab đầu tiên

        # Đợi người dùng nhấn Enter trước khi thoát
        input("\nNhấn Enter để kết thúc chương trình và đóng trình duyệt...")

        # Đóng trình duyệt sau khi nhấn Enter
        self.driver.quit()


def main():
    WEBSITE_URL = "http://nhomdich2.manhuavn.top/Admin.aspx"
    DIRECT_URL = "http://nhomdich2.manhuavn.top/Admin.aspx?mod=11&PID=67c8a4160557c835a44de504"
    USERNAME = "0877341711"
    PASSWORD = "daimieu01234567"
    BASE_FOLDER = "/Users/tuananhdo/Desktop/7"

    uploader = ChapterUploader(WEBSITE_URL, USERNAME, PASSWORD, BASE_FOLDER, DIRECT_URL)
    uploader.batch_upload()


if __name__ == "__main__":
    main()