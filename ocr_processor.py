import os
import pytesseract
from PIL import Image
import google.generativeai as genai
from docx import Document
import re

class OCRProcessor:
    def __init__(self, api_key=None):
        # Cấu hình Gemini nếu có API key
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
        
        # Đường dẫn đến Tesseract
        pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

    def process_image(self, image_path):
        """Xử lý OCR cho một ảnh với nhiều ngôn ngữ"""
        try:
            # Đọc ảnh
            with Image.open(image_path) as img:
                # Thực hiện OCR với nhiều ngôn ngữ
                text = pytesseract.image_to_string(img, lang='vie+eng+chi_sim+jpn+kor')
                return text.strip()
        except Exception as e:
            print(f"Lỗi khi xử lý OCR cho {image_path}: {str(e)}")
            return ""

    def translate_text(self, text, target_lang, genre=None):
        """Dịch văn bản sang ngôn ngữ đích"""
        if not self.model or not text:
            return text

        try:
            # Xác định phong cách dựa trên thể loại
            style_guide = ""
            if genre:
                style_guides = {
                    'drama': 'tình cảm sâu lắng, cảm xúc',
                    'adult': 'người lớn, chín chắn nhưng tế nhị',
                    'romance': 'lãng mạn, ngọt ngào',
                    'comedy': 'hài hước, vui nhộn',
                    'bl': 'tình cảm nam nam tinh tế',
                    'wuxia': 'kiếm hiệp, võ thuật cổ trang',
                    'action': 'hành động, gay cấn'
                }
                style_guide = style_guides.get(genre, '')

            # Xác định ngôn ngữ đích
            lang_guides = {
                'vi': 'tiếng Việt',
                'en': 'tiếng Anh',
                'ja': 'tiếng Nhật',
                'ko': 'tiếng Hàn',
                'zh': 'tiếng Trung'
            }
            lang_guide = lang_guides.get(target_lang, 'tiếng Việt')

            prompt = f"""
            Đây là văn bản được trích xuất từ truyện tranh/manga:
            {text}
            
            Hãy dịch và chỉnh sửa văn bản theo yêu cầu sau:
            1. Dịch sang {lang_guide} với văn phong tự nhiên, dễ đọc
            2. Giữ nguyên ý nghĩa và cảm xúc của nguyên tác
            3. Sửa lỗi chính tả và dấu câu
            4. Định dạng văn bản cho dễ đọc
            {f'5. Phong cách phù hợp với thể loại {style_guide}' if style_guide else ''}
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"Lỗi khi dịch văn bản: {str(e)}")
            return text

    def save_to_word(self, text, output_path):
        """Lưu văn bản vào file Word"""
        try:
            doc = Document()
            
            # Tách văn bản thành các đoạn
            paragraphs = text.split('\n')
            
            # Thêm từng đoạn vào document
            for para in paragraphs:
                if para.strip():  # Chỉ thêm đoạn không trống
                    doc.add_paragraph(para.strip())
            
            # Lưu file
            doc.save(output_path)
            return True
        except Exception as e:
            print(f"Lỗi khi lưu file Word: {str(e)}")
            return False

def process_folder(folder_path, api_key=None, genre=None, target_langs=None):
    """Xử lý tất cả ảnh trong thư mục và tạo file Word cho mỗi ngôn ngữ"""
    try:
        processor = OCRProcessor(api_key)
        
        # Lấy danh sách ảnh
        image_files = [f for f in os.listdir(folder_path) if
                      f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        
        if not image_files:
            raise Exception("Không tìm thấy ảnh trong thư mục")
            
        # Sắp xếp ảnh theo số trong tên file
        image_files.sort(key=lambda x: int(re.search(r'\d+', x).group() if re.search(r'\d+', x) else 0))
        
        # Ngôn ngữ mặc định nếu không được chỉ định
        if not target_langs:
            target_langs = ['vi']
        
        # Xử lý từng ảnh
        output_files = {lang: [] for lang in target_langs}
        for idx, img_file in enumerate(image_files, 1):
            img_path = os.path.join(folder_path, img_file)
            
            # Thực hiện OCR
            text = processor.process_image(img_path)
            
            if text:
                # Dịch và lưu cho từng ngôn ngữ
                for lang in target_langs:
                    # Dịch văn bản nếu có API key
                    translated_text = text
                    if api_key:
                        translated_text = processor.translate_text(text, lang, genre)
                    
                    # Tạo tên file Word theo định dạng số thứ tự
                    word_filename = f"{idx}_{lang}.docx"
                    output_path = os.path.join(folder_path, word_filename)
                    
                    # Lưu vào file Word
                    if processor.save_to_word(translated_text, output_path):
                        output_files[lang].append(output_path)
        
        if not any(output_files.values()):
            raise Exception("Không thể trích xuất được văn bản từ các ảnh")
        
        return output_files
        
    except Exception as e:
        print(f"Lỗi trong quá trình xử lý OCR: {str(e)}")
        raise 