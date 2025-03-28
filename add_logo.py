from PIL import Image
import os

class LogoProcessor:
    def __init__(self):
        self.logo_positions = {
            'top_left': (10, 10),
            'top_right': (-10, 10),
            'bottom_left': (10, -10),
            'bottom_right': (-10, -10),
            'center': (0, 0),
            'top_center': (0, 10),
            'bottom_center': (0, -10),
            'left_center': (10, 0),
            'right_center': (-10, 0)
        }
    
    def add_logo(self, image_path, logo_path, position='top_left', scale=0.1):
        """
        Thêm logo vào ảnh gốc
        
        Args:
            image_path: Đường dẫn đến ảnh gốc
            logo_path: Đường dẫn đến file logo
            position: Vị trí đặt logo (top_left, top_right, bottom_left, bottom_right, center, top_center, bottom_center, left_center, right_center)
            scale: Tỷ lệ kích thước logo so với ảnh gốc (0.1 = 10%)
            
        Returns:
            Ảnh đã thêm logo
        """
        try:
            # Mở ảnh gốc và logo
            with Image.open(image_path) as img:
                # Chuyển ảnh gốc sang RGB nếu cần
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                # Mở logo
                with Image.open(logo_path) as logo:
                    # Chuyển logo sang RGBA nếu cần
                    if logo.mode != 'RGBA':
                        logo = logo.convert('RGBA')
                    
                    # Tính toán kích thước logo
                    logo_width = int(img.width * scale)
                    logo_height = int(logo_width * (logo.height / logo.width))
                    
                    # Resize logo giữ nguyên tỷ lệ
                    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                    
                    # Tính toán vị trí đặt logo
                    x_offset, y_offset = self.logo_positions.get(position, (10, 10))
                    
                    # Tính toán vị trí cuối cùng
                    if x_offset < 0:  # Căn phải
                        x = img.width - logo.width + x_offset
                    else:  # Căn trái
                        x = x_offset
                        
                    if y_offset < 0:  # Căn dưới
                        y = img.height - logo.height + y_offset
                    else:  # Căn trên
                        y = y_offset
                    
                    # Tạo ảnh mới với kênh alpha
                    result = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    
                    # Paste ảnh gốc vào
                    result.paste(img, (0, 0))
                    
                    # Paste logo vào vị trí đã tính
                    result.paste(logo, (x, y), logo)
                    
                    # Chuyển về RGB
                    result = result.convert('RGB')
                    
                    return result
                    
        except Exception as e:
            print(f"Lỗi khi xử lý ảnh {image_path}: {str(e)}")
            raise Exception(f"Lỗi khi xử lý ảnh {image_path}: {str(e)}")
    
    def process_folder(self, folder_path, logo_path, position, scale=0.1):
        """
        Xử lý tất cả ảnh trong thư mục
        """
        try:
            # Xử lý từng ảnh
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    input_path = os.path.join(folder_path, filename)
                    
                    try:
                        # Thêm logo vào ảnh
                        processed_img = self.add_logo(input_path, logo_path, position, scale)
                        
                        # Lưu ảnh đã xử lý
                        if processed_img:
                            output_path = os.path.join(folder_path, f'processed_{filename}')
                            processed_img.save(output_path, 'JPEG', quality=95)
                            return output_path
                    except Exception as e:
                        print(f"Lỗi khi xử lý file {filename}: {str(e)}")
                        continue
            
            return None
            
        except Exception as e:
            raise Exception(f"Lỗi khi xử lý thư mục: {str(e)}") 