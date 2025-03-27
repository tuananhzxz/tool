import os
import re


def rename_image_files(folder_path):
    """
    Đổi tên các tệp ảnh trong thư mục, chỉ giữ lại phần tên chính.

    Args:
        folder_path (str): Đường dẫn đến thư mục chứa ảnh
    """
    # Kiểm tra đường dẫn thư mục có tồn tại không
    if not os.path.isdir(folder_path):
        print(f"Thư mục '{folder_path}' không tồn tại!")
        return

    # Đếm số tệp đã xử lý
    count_renamed = 0
    count_skipped = 0

    # Lặp qua tất cả tệp trong thư mục
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        # Chỉ xử lý các tệp (không xử lý thư mục con)
        if os.path.isfile(file_path):
            # Tìm tên tệp theo mẫu (như "002.jpeg")
            match = re.search(r'([^&]+\.(jpeg|jpg|png|gif|bmp|webp))', filename, re.IGNORECASE)

            if match:
                new_filename = match.group(1)
                new_file_path = os.path.join(folder_path, new_filename)

                # Kiểm tra nếu tên mới đã tồn tại và khác với tên hiện tại
                if new_file_path != file_path:
                    if os.path.exists(new_file_path):
                        print(f"Bỏ qua '{filename}' vì '{new_filename}' đã tồn tại!")
                        count_skipped += 1
                    else:
                        os.rename(file_path, new_file_path)
                        print(f"Đã đổi tên: '{filename}' -> '{new_filename}'")
                        count_renamed += 1
                else:
                    print(f"Bỏ qua '{filename}' vì tên tệp đã đúng định dạng")
                    count_skipped += 1
            else:
                print(f"Bỏ qua '{filename}' vì không phù hợp với mẫu tên ảnh")
                count_skipped += 1

    print(f"\nĐã đổi tên {count_renamed} tệp và bỏ qua {count_skipped} tệp.")


if __name__ == "__main__":
    folder_path = input("Nhập đường dẫn đến thư mục chứa ảnh: ")
    rename_image_files(folder_path)