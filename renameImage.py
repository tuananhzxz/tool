import os
import re


def rename_files(folder_path):
    # Lấy danh sách tất cả các file ảnh trong thư mục
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    
    if not files:
        print("Không tìm thấy file ảnh nào")
        return

    # Tìm số trong tên file
    def get_number(filename):
        match = re.search(r'(\d+)', filename)
        if match:
            return int(match.group(1))
        return 0  # Trả về 0 nếu không tìm thấy số

    # Sắp xếp files theo số trong tên
    files.sort(key=get_number)
    
    # Tạo ánh xạ tên mới, bắt đầu từ 1
    file_mapping = {}
    next_number = 1
    
    for filename in files:
        # Lấy phần mở rộng của file
        ext = os.path.splitext(filename)[1].lower()
        # Tạo tên mới
        new_name = f"{next_number}{ext}"
        file_mapping[filename] = new_name
        next_number += 1

    # Đổi tên các file
    for old_name, new_name in file_mapping.items():
        # Tạo tên tạm thời để tránh xung đột
        temp_name = f"temp_{old_name}"
        old_path = os.path.join(folder_path, old_name)
        temp_path = os.path.join(folder_path, temp_name)
        new_path = os.path.join(folder_path, new_name)

        try:
            os.rename(old_path, temp_path)
        except Exception as e:
            print(f"Lỗi khi đổi tên {old_name}: {str(e)}")
            continue

    # Đổi từ tên tạm sang tên mới
    for old_name, new_name in file_mapping.items():
        temp_name = f"temp_{old_name}"
        temp_path = os.path.join(folder_path, temp_name)
        new_path = os.path.join(folder_path, new_name)
        
        try:
            os.rename(temp_path, new_path)
            print(f"Đã đổi tên: {old_name} -> {new_name}")
        except Exception as e:
            print(f"Lỗi khi đổi tên {temp_name}: {str(e)}")

    print(f"Đã đổi tên {len(file_mapping)} files thành công!")


# Sử dụng tool
if __name__ == "__main__":
    main_folder = "34"  # Thư mục chính

    if not os.path.exists(main_folder):
        print(f"Không tìm thấy thư mục: {main_folder}")
    else:
        print("=== Bắt đầu xử lý ===")
        rename_files(main_folder)