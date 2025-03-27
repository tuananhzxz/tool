import os
from PIL import Image
import google.generativeai as genai
import numpy as np
from io import BytesIO

class SpeechBubbleProcessor:
    def __init__(self, api_key=None):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro-vision')
    
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
                
                # Lưu ảnh vào buffer để gửi cho Gemini
                img_buffer = BytesIO()
                img.save(img_buffer, format='JPEG')
                img_buffer.seek(0)
                
                # Sử dụng Gemini để nhận diện bóng thoại
                if self.api_key:
                    prompt = """
                    Hãy phân tích ảnh và cho tôi biết:
                    1. Vị trí của các bóng thoại (tọa độ x, y, chiều rộng, chiều cao)
                    2. Màu nền của bóng thoại
                    3. Độ trong suốt của bóng thoại
                    """
                    
                    response = self.model.generate_content([prompt, img_buffer])
                    bubble_info = response.text
                    
                    # Xử lý thông tin từ Gemini để xóa bóng thoại
                    # TODO: Implement bubble removal logic based on Gemini response
                
                # Tạm thời trả về ảnh gốc
                return img
                
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