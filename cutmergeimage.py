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
        Ghép các phần ảnh đã cắt thành một ảnh hoàn chỉnh theo chiều ngang
        """
        try:
            # Sắp xếp ảnh theo số thứ tự
            self.image_files.sort(key=lambda x: int(re.search(r'\d+', x).group() if re.search(r'\d+', x) else 0))
            
            # Tính số nhóm cần ghép
            total_images = len(self.image_files)
            num_groups = (total_images + images_per_group - 1) // images_per_group
            
            # Mở ảnh đầu tiên để lấy kích thước
            with Image.open(os.path.join(self.folder_path, self.image_files[0])) as first_img:
                part_width = first_img.width
                part_height = first_img.height

            # Ghép từng nhóm ảnh
            for group_idx in range(num_groups):
                start_idx = group_idx * images_per_group
                end_idx = min(start_idx + images_per_group, total_images)
                group_images = self.image_files[start_idx:end_idx]
                
                # Tạo ảnh mới với chiều cao bằng tổng các phần trong nhóm
                total_height = part_height * len(group_images)
                result = Image.new('RGB', (part_width, total_height))

                # Ghép các phần ảnh theo chiều dọc
                for idx, img_file in enumerate(group_images):
                    with Image.open(os.path.join(self.folder_path, img_file)) as img:
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')
                        result.paste(img, (0, idx * part_height))

                # Lưu ảnh ghép với tên là tên thư mục + số nhóm
                output_path = os.path.join(self.folder_path, f"{self.folder_name}_group_{group_idx + 1}.jpg")
                result.save(output_path, quality=95)

            # Xóa các ảnh gốc
            for img_file in self.image_files:
                os.remove(os.path.join(self.folder_path, img_file))

            print(f"Đã ghép thành công thành {num_groups} ảnh")

        except Exception as e:
            raise Exception(f"Lỗi khi ghép ảnh: {str(e)}")

    def split_images(self, split_parts):
        """
        Cắt ảnh thành nhiều phần bằng nhau theo chiều ngang
        """
        if len(self.image_files) != 1:
            raise Exception("Vui lòng chỉ chọn một ảnh để cắt")

        try:
            input_image = self.image_files[0]
            with Image.open(os.path.join(self.folder_path, input_image)) as img:
                if img.mode == 'RGBA':
                    img = img.convert('RGB')

                width, height = img.size
                part_height = height // split_parts

                # Cắt và lưu từng phần theo chiều ngang
                for i in range(split_parts):
                    top = i * part_height
                    bottom = top + part_height
                    part = img.crop((0, top, width, bottom))
                    
                    # Lưu với tên là tên thư mục + số thứ tự
                    output_path = os.path.join(self.folder_path, f"{self.folder_name}_{i+1}.jpg")
                    part.save(output_path, quality=95)

            # Xóa ảnh gốc
            os.remove(os.path.join(self.folder_path, input_image))
            print(f"Đã cắt ảnh thành {split_parts} phần")

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