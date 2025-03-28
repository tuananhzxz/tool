import os
from PIL import Image, ImageDraw, ImageEnhance
import google.generativeai as genai
import numpy as np
from io import BytesIO
import cv2

class SpeechBubbleProcessor:
    def __init__(self, api_key=None):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
    
    def process_image(self, image_path):
        """
        Xử lý ảnh để xóa bóng thoại
        """
        try:
            # Mở ảnh
            with Image.open(image_path) as img:
                # Chuyển ảnh sang RGB nếu cần
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Chuyển sang numpy array để xử lý với OpenCV
                img_array = np.array(img)
                
                # Chuyển sang grayscale
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                
                # Áp dụng Gaussian blur để giảm nhiễu
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                
                # Phát hiện cạnh với Canny
                edges = cv2.Canny(blurred, 50, 150)
                
                # Tìm contours
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Lọc contours theo diện tích và tỷ lệ khung hình
                min_area = 1000  # Diện tích tối thiểu
                max_area = img_array.shape[0] * img_array.shape[1] * 0.8  # Diện tích tối đa (80% ảnh)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if min_area < area < max_area:
                        # Lấy khung chứa contour
                        x, y, w, h = cv2.boundingRect(contour)
                        
                        # Tính tỷ lệ khung hình
                        aspect_ratio = float(w) / h
                        
                        # Lọc theo tỷ lệ khung hình (bóng thoại thường có tỷ lệ 1:1 đến 3:1)
                        if 0.5 < aspect_ratio < 3.0:
                            # Tạo mask cho vùng bóng thoại
                            mask = np.zeros_like(gray)
                            cv2.drawContours(mask, [contour], -1, (255), -1)
                            
                            # Áp dụng mask để xóa vùng bóng thoại
                            img_array[mask == 255] = [255, 255, 255]  # Thay thế bằng màu trắng
                
                # Chuyển lại thành PIL Image
                result_img = Image.fromarray(img_array)
                
                # Tăng độ tương phản
                enhancer = ImageEnhance.Contrast(result_img)
                result_img = enhancer.enhance(1.2)
                
                return result_img
                
        except Exception as e:
            raise Exception(f"Lỗi khi xử lý ảnh: {str(e)}")
    
    def process_folder(self, folder_path):
        """
        Xử lý tất cả ảnh trong thư mục
        """
        try:
            # Tạo thư mục output
            output_dir = os.path.join(folder_path, 'processed')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Xử lý từng ảnh
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    input_path = os.path.join(folder_path, filename)
                    output_path = os.path.join(output_dir, f'processed_{filename}')
                    
                    # Xử lý ảnh
                    processed_img = self.process_image(input_path)
                    
                    # Lưu ảnh đã xử lý
                    processed_img.save(output_path, quality=95)
            
            return output_dir
            
        except Exception as e:
            raise Exception(f"Lỗi khi xử lý thư mục: {str(e)}") 