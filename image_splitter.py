from PIL import Image
import os
import shutil


def split_image(image_path, chunk_size=800):
    # Tạo thư mục tạm để lưu các phần đã cắt
    temp_dir = "temp_chunks"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    base_name = os.path.splitext(os.path.basename(image_path))[0]

    # Mở ảnh
    with Image.open(image_path) as img:
        # Lấy kích thước ảnh
        width, height = img.size
        print(f"Kích thước ảnh gốc: {width}x{height}")

        # Tính số phần cần cắt theo chiều ngang và dọc
        num_cols = (width + chunk_size - 1) // chunk_size
        num_rows = (height + chunk_size - 1) // chunk_size
        total_chunks = num_rows * num_cols

        print(f"Sẽ cắt thành {total_chunks} phần {chunk_size}x{chunk_size}")

        # Biến đếm cho tên file
        chunk_count = 0

        # Cắt và lưu từng phần
        for row in range(num_rows):
            for col in range(num_cols):
                chunk_count += 1

                # Tính toạ độ cho phần cắt
                left = col * chunk_size
                top = row * chunk_size
                right = min((col + 1) * chunk_size, width)
                bottom = min((row + 1) * chunk_size, height)

                # Cắt phần ảnh
                chunk = img.crop((left, top, right, bottom))

                # Nếu phần cắt không đủ 800x800, tạo ảnh mới với nền trắng
                if chunk.size != (chunk_size, chunk_size):
                    new_chunk = Image.new('RGB', (chunk_size, chunk_size), 'white')
                    new_chunk.paste(chunk, (0, 0))
                    chunk = new_chunk

                # Tạo tên file cho phần đã cắt
                output_path = os.path.join(
                    temp_dir,
                    f'{base_name}_{chunk_count}.jpg'
                )

                # Lưu phần đã cắt
                chunk.save(output_path)
                print(f'Đã lưu phần {chunk_count}/{total_chunks}: {output_path}')

    # Xóa ảnh gốc
    os.remove(image_path)

    # Di chuyển các phần đã cắt vào thư mục gốc
    for filename in os.listdir(temp_dir):
        if filename.startswith(base_name):
            src_path = os.path.join(temp_dir, filename)
            dst_path = os.path.join(os.path.dirname(image_path), filename)
            shutil.move(src_path, dst_path)

    # Xóa thư mục tạm
    if os.path.exists(temp_dir):
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass
    print(f"\nHoàn thành xử lý ảnh {image_path}")


def process_folder(folder_path):
    """Xử lý đệ quy tất cả các ảnh trong thư mục và các thư mục con"""
    # Các định dạng ảnh được hỗ trợ
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')

    print(f"\nĐang quét thư mục: {folder_path}")

    # Kiểm tra xem thư mục có tồn tại không
    if not os.path.exists(folder_path):
        print(f"Thư mục không tồn tại: {folder_path}")
        return

    # Lặp qua tất cả các mục trong thư mục
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)

        # Nếu là thư mục, xử lý đệ quy
        if os.path.isdir(item_path):
            print(f"\nTìm thấy thư mục con: {item_path}")
            process_folder(item_path)

        # Nếu là file ảnh, xử lý ảnh
        elif item.lower().endswith(supported_formats):
            print(f"\nĐang xử lý ảnh: {item}")
            try:
                split_image(item_path)
            except Exception as e:
                print(f"Lỗi khi xử lý ảnh {item}: {str(e)}")


if __name__ == "__main__":
    # Danh sách các thư mục gốc cần xử lý
    root_folders = [
        "7",
        # Thêm các thư mục gốc khác vào đây
    ]

    # Xử lý từng thư mục gốc và tất cả thư mục con của nó
    for folder in root_folders:
        process_folder(folder)

    print("\nĐã hoàn thành xử lý tất cả thư mục")