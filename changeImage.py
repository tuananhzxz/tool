import os
from PIL import Image
import sys


def clear_screen():
    """Xóa màn hình terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')


def show_menu():
    """Hiển thị menu chính"""
    print("\n=== CÔNG CỤ CHUYỂN ĐỔI ẢNH ===")
    print("1. JPEG -> WebP")
    print("2. WebP -> JPEG")
    print("3. PNG -> WebP")
    print("4. WebP -> PNG")
    print("5. JPEG -> PNG")
    print("6. PNG -> JPEG")
    print("0. Thoát")
    print("================================")
    return input("Vui lòng chọn: ")


def get_folders():
    """Lấy đường dẫn thư mục input và output từ người dùng"""
    input_folder = input("\nNhập đường dẫn thư mục chứa ảnh gốc: ").strip()
    output_folder = input("Nhập đường dẫn thư mục lưu ảnh đã chuyển đổi: ").strip()

    # Kiểm tra thư mục input tồn tại
    if not os.path.exists(input_folder):
        print(f"Lỗi: Thư mục '{input_folder}' không tồn tại!")
        return None, None

    # Tạo thư mục output nếu chưa tồn tại
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    return input_folder, output_folder


def convert_images(input_folder, output_folder, source_format, target_format):
    """
    Chuyển đổi tất cả ảnh từ định dạng nguồn sang định dạng đích
    """
    # Ánh xạ định dạng file
    format_mapping = {
        'JPEG': ['.jpg', '.jpeg'],
        'PNG': ['.png'],
        'WEBP': ['.webp']
    }

    source_extensions = format_mapping[source_format]
    converted_count = 0
    error_count = 0

    print("\nĐang chuyển đổi ảnh...")

    for filename in os.listdir(input_folder):
        name, ext = os.path.splitext(filename)
        ext = ext.lower()

        # Kiểm tra nếu file có định dạng nguồn phù hợp
        if ext in source_extensions:
            input_path = os.path.join(input_folder, filename)

            # Tạo tên file mới với định dạng đích
            if target_format == 'WEBP':
                new_filename = f"{name}.webp"
            elif target_format == 'JPEG':
                new_filename = f"{name}.jpg"
            else:  # PNG
                new_filename = f"{name}.png"

            output_path = os.path.join(output_folder, new_filename)

            try:
                # Mở và chuyển đổi ảnh
                with Image.open(input_path) as img:
                    # Chuyển sang RGB nếu ảnh ở chế độ RGBA
                    if img.mode == 'RGBA' and target_format == 'JPEG':
                        img = img.convert('RGB')

                    # Lưu ảnh với định dạng mới
                    if target_format == 'WEBP':
                        img.save(output_path, 'WEBP', quality=90, method=6)
                    elif target_format == 'JPEG':
                        img.save(output_path, 'JPEG', quality=95)
                    else:  # PNG
                        img.save(output_path, 'PNG')

                print(f"✓ Đã chuyển đổi: {filename} -> {new_filename}")
                converted_count += 1

            except Exception as e:
                print(f"✗ Lỗi khi chuyển đổi {filename}: {str(e)}")
                error_count += 1

    print(f"\nHoàn thành!")
    print(f"- Số ảnh đã chuyển đổi thành công: {converted_count}")
    print(f"- Số ảnh bị lỗi: {error_count}")


def main():
    while True:
        choice = show_menu()

        # Ánh xạ lựa chọn menu với các định dạng chuyển đổi
        conversion_map = {
            '1': ('JPEG', 'WEBP'),
            '2': ('WEBP', 'JPEG'),
            '3': ('PNG', 'WEBP'),
            '4': ('WEBP', 'PNG'),
            '5': ('JPEG', 'PNG'),
            '6': ('PNG', 'JPEG'),
            '0': None
        }

        if choice not in conversion_map:
            print("\nLựa chọn không hợp lệ! Vui lòng thử lại.")
            continue

        if choice == '0':
            print("\nCảm ơn bạn đã sử dụng công cụ!")
            break

        # Lấy định dạng nguồn và đích từ lựa chọn
        source_format, target_format = conversion_map[choice]

        # Lấy đường dẫn thư mục
        input_folder, output_folder = get_folders()
        if input_folder and output_folder:
            convert_images(input_folder, output_folder, source_format, target_format)

        input("\nNhấn Enter để tiếp tục...")
        clear_screen()


if __name__ == "__main__":
    main()