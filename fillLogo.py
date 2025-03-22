import os
import cv2
import numpy as np


def find_suitable_white_region(image, logo_size):
    """Tìm vùng trắng phù hợp để chèn logo."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Tạo mask cho vùng trắng
    _, white_mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)

    # Tạo kernel cho việc kiểm tra vùng trắng
    kernel_size = (logo_size[1], logo_size[0])
    kernel = np.ones(kernel_size) / (kernel_size[0] * kernel_size[1])

    # Tính toán tỷ lệ điểm trắng trong mỗi vùng có kích thước bằng logo
    white_ratio_map = cv2.filter2D((white_mask / 255.0), -1, kernel)

    # Tìm các cạnh trong ảnh để tránh đặt logo gần đối tượng
    edges = cv2.Canny(gray, 50, 150)
    edge_density = cv2.filter2D((edges / 255.0), -1, kernel)

    # Kết hợp white_ratio_map và edge_density để tìm vị trí tốt nhất
    # Vùng càng trắng và càng ít cạnh càng tốt
    suitability_map = white_ratio_map - edge_density

    # Tìm vị trí tốt nhất
    best_score = np.max(suitability_map)
    if best_score < 0.9:  # Ngưỡng cho vùng đủ trắng
        print("Không tìm thấy vùng trắng phù hợp")
        return None

    y, x = np.unravel_index(np.argmax(suitability_map), suitability_map.shape)

    # Kiểm tra xem vùng này có thực sự phù hợp không
    roi = white_mask[y:y + logo_size[1], x:x + logo_size[0]]
    white_pixel_ratio = np.sum(roi == 255) / (logo_size[0] * logo_size[1])

    if white_pixel_ratio < 0.9:  # Yêu cầu ít nhất 90% pixel trắng
        print("Không tìm thấy vùng đủ trắng")
        return None

    return (x, y)


def insert_logo(image_path, logo_path):
    """Chèn logo vào ảnh tại vị trí trắng phù hợp."""
    # Đọc ảnh gốc
    image = cv2.imread(image_path)
    if image is None:
        print(f"Không thể đọc ảnh: {image_path}")
        return False

    # Đọc logo
    logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
    if logo is None:
        print(f"Không thể đọc logo: {logo_path}")
        return False

    # Điều chỉnh kích thước logo
    target_width = int(image.shape[1] * 0.15)  # Giảm xuống 15% chiều rộng ảnh
    aspect_ratio = logo.shape[1] / logo.shape[0]
    target_height = int(target_width / aspect_ratio)
    logo_resized = cv2.resize(logo, (target_width, target_height))

    # Tìm vị trí phù hợp
    position = find_suitable_white_region(image, (target_width, target_height))
    if position is None:
        print(f"Không tìm được vị trí phù hợp trong ảnh: {image_path}")
        return False

    try:
        x, y = position
        roi = image[y:y + target_height, x:x + target_width]

        if len(logo_resized.shape) > 2 and logo_resized.shape[2] == 4:
            # Xử lý logo có alpha channel
            alpha = logo_resized[:, :, 3] / 255.0
            alpha = np.expand_dims(alpha, axis=2)
            for c in range(3):
                roi[:, :, c] = roi[:, :, c] * (1 - alpha[:, :, 0]) + \
                               logo_resized[:, :, c] * alpha[:, :, 0]
        else:
            # Xử lý logo không có alpha channel
            if len(logo_resized.shape) == 3:
                roi[:] = logo_resized[:, :, :3]
            else:
                roi[:] = cv2.cvtColor(logo_resized, cv2.COLOR_GRAY2BGR)

        image[y:y + target_height, x:x + target_width] = roi
        cv2.imwrite(image_path, image)
        print(f"Đã chèn logo thành công vào: {image_path}")
        return True
    except Exception as e:
        print(f"Lỗi khi xử lý ảnh: {str(e)}")
        return False


def process_directory(directory_path, logo_path):
    """Xử lý đệ quy tất cả ảnh trong thư mục và các thư mục con."""
    processed_count = 0

    for item in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item)

        if os.path.isfile(item_path):
            if item.lower().endswith(('.png', '.jpg', '.jpeg')):
                print(f"Đang xử lý: {item_path}")
                if insert_logo(item_path, logo_path):
                    processed_count += 1

        elif os.path.isdir(item_path):
            print(f"Đang xử lý thư mục: {item_path}")
            sub_count = process_directory(item_path, logo_path)
            processed_count += sub_count

    return processed_count


# Sử dụng tool
if __name__ == "__main__":
    main_folder = "28"  # Thư mục chính
    logo_path = "logotrong.png"

    if not os.path.exists(main_folder):
        print(f"Không tìm thấy thư mục: {main_folder}")
    elif not os.path.exists(logo_path):
        print(f"Không tìm thấy file logo: {logo_path}")
    else:
        print("=== Bắt đầu xử lý ===")
        total_processed = process_directory(main_folder, logo_path)
        print(f"=== Đã xử lý xong {total_processed} ảnh ===")