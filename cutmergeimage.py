import os
from PIL import Image
import math
import shutil
import re


class ImageProcessor:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.folder_name = os.path.basename(folder_path)
        self.image_files = [f for f in os.listdir(folder_path) if
                            f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if not self.image_files:
            raise Exception(f"Không tìm thấy ảnh trong thư mục {folder_path}")

    def combine_images(self, images_per_group):
        """
        Ghép các phần ảnh đã cắt thành một ảnh hoàn chỉnh theo chiều dọc
        """
        try:
            result_files = []
            # Sắp xếp ảnh theo số thứ tự
            self.image_files.sort(key=lambda x: int(re.search(r'\d+', x).group() if re.search(r'\d+', x) else 0))
            
            # Tính số nhóm cần ghép
            total_images = len(self.image_files)
            num_groups = (total_images + images_per_group - 1) // images_per_group
            
            # Mở và đọc tất cả ảnh trong nhóm
            for group_idx in range(num_groups):
                start_idx = group_idx * images_per_group
                end_idx = min(start_idx + images_per_group, total_images)
                group_images = self.image_files[start_idx:end_idx]
                
                # Đọc và xử lý các ảnh trong nhóm
                image_parts = []
                max_width = 0
                total_height = 0
                
                for img_file in group_images:
                    with Image.open(os.path.join(self.folder_path, img_file)) as img:
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')
                        image_parts.append(img.copy())
                        max_width = max(max_width, img.width)
                        total_height += img.height
                
                # Tạo ảnh mới
                result = Image.new('RGB', (max_width, total_height))
                
                # Ghép các phần ảnh
                y_offset = 0
                for img in image_parts:
                    # Đảm bảo ảnh có cùng chiều rộng
                    if img.width != max_width:
                        img = img.resize((max_width, img.height), Image.Resampling.LANCZOS)
                    
                    # Ghép ảnh vào kết quả
                    result.paste(img, (0, y_offset))
                    y_offset += img.height
                
                # Lưu ảnh ghép
                output_path = os.path.join(self.folder_path, f"{self.folder_name}_group_{group_idx + 1}.jpg")
                result.save(output_path, quality=95)
                result_files.append(output_path)
                
                # Giải phóng bộ nhớ
                for img in image_parts:
                    img.close()

            # Xóa các ảnh gốc
            for img_file in self.image_files:
                os.remove(os.path.join(self.folder_path, img_file))

            print(f"Đã ghép thành công thành {num_groups} ảnh")
            return result_files

        except Exception as e:
            raise Exception(f"Lỗi khi ghép ảnh: {str(e)}")

    def split_images(self, min_height):
        """
        Cắt ảnh thành nhiều phần dựa trên chiều cao tối thiểu
        :param min_height: Chiều cao tối thiểu cho mỗi phần (pixel)
        :return: Danh sách đường dẫn các file đã cắt
        """
        try:
            result_files = []
            
            # Xử lý từng ảnh trong thư mục
            for input_image in self.image_files:
                base_name = os.path.splitext(input_image)[0]
                
                with Image.open(os.path.join(self.folder_path, input_image)) as img:
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')

                    width, height = img.size
                    
                    # Tính số phần cần cắt dựa trên chiều cao tối thiểu
                    num_parts = math.ceil(height / min_height)
                    part_height = height // num_parts  # Chiều cao thực tế của mỗi phần
                    
                    # Cắt và lưu từng phần
                    for i in range(num_parts):
                        top = i * part_height
                        # Phần cuối cùng sẽ lấy đến hết chiều cao của ảnh
                        bottom = height if i == num_parts - 1 else (i + 1) * part_height
                        part = img.crop((0, top, width, bottom))
                        
                        # Tạo tên file với số thứ tự
                        output_path = os.path.join(self.folder_path, f"{base_name}_part_{i+1}.jpg")
                        part.save(output_path, quality=95)
                        result_files.append(output_path)

                # Xóa ảnh gốc sau khi đã cắt xong
                os.remove(os.path.join(self.folder_path, input_image))
                print(f"Đã cắt ảnh {input_image} thành {num_parts} phần")

            return result_files

        except Exception as e:
            raise Exception(f"Lỗi khi cắt ảnh: {str(e)}")


def main():
    folder_path = input("Nhập folder: ").strip()

    try:
        processor = ImageProcessor(folder_path)

        # while True:
        #     print("\n=== MENU XỬ LÝ ẢNH ===")
        #     print("1. Cắt ảnh")
        #     print("2. Ghép ảnh")
        #     print("3. Thoát")
        #
        #     choice = input("\nChọn chức năng (1-3): ").strip()
        #
        #     if choice == "1":
        #         parts = int(input("Nhập số phần muốn cắt mỗi ảnh: "))
        #         processor.split_images(parts)
        #
        #     elif choice == "2":
        #         images_per_group = int(input("Nhập số ảnh muốn ghép vào một nhóm: "))
        #         processor.combine_images(images_per_group)
        #
        #     elif choice == "3":
        #         print("Cảm ơn bạn đã sử dụng chương trình!")
        #         break
        #
        #     else:
        #         print("Lựa chọn không hợp lệ. Vui lòng chọn lại.")
        images_per_group = int(input("Nhập số ảnh muốn ghép vào một nhóm: "))
        processor.combine_images(images_per_group)

    except Exception as e:
        print(f"Lỗi: {str(e)}")


if __name__ == "__main__":
    main()