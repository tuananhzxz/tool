import os
import cv2
import numpy as np
from math import ceil


def split_image(image_path, output_folder, num_segments=3):
    """
    Split a single image into equal segments with fixed dimensions
    """
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Không thể đọc ảnh: {image_path}")
        return

    # Get image dimensions
    height, width = img.shape[:2]

    # Calculate segment height
    segment_height = height // num_segments

    # Create output folder if not exists
    os.makedirs(output_folder, exist_ok=True)

    # Get base filename without extension
    base_filename = os.path.splitext(os.path.basename(image_path))[0]

    # Split and save segments
    for i in range(num_segments):
        # Calculate segment coordinates
        start_y = i * segment_height
        end_y = start_y + segment_height if i < num_segments - 1 else height

        # Extract segment
        segment = img[start_y:end_y, :]

        # Generate output filename with zero-padded numbering
        output_filename = f"{base_filename}_{i + 1:03d}.jpg"
        output_path = os.path.join(output_folder, output_filename)

        # Save segment
        cv2.imwrite(output_path, segment)
        print(f"Đã lưu phần: {output_filename} - Kích thước: {segment.shape[1]}x{segment.shape[0]}px")


def batch_process_images(input_folder, output_folder, num_segments=3):
    """
    Process all images in the input folder
    """
    # Create output folder if not exists
    os.makedirs(output_folder, exist_ok=True)

    # Supported image formats
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')

    # Get all image files
    image_files = [f for f in os.listdir(input_folder)
                   if f.lower().endswith(supported_formats)]

    # Sort files to maintain order
    image_files.sort()

    # Process each image
    for filename in image_files:
        input_path = os.path.join(input_folder, filename)
        print(f"\nXử lý ảnh: {filename}")

        try:
            split_image(input_path, output_folder, num_segments)
        except Exception as e:
            print(f"Lỗi khi xử lý {filename}: {str(e)}")


if __name__ == "__main__":
    # Get input from user
    input_folder = input("Nhập đường dẫn thư mục chứa ảnh gốc: ").strip()
    output_folder = input("Nhập đường dẫn thư mục lưu ảnh đã cắt: ").strip()

    try:
        num_segments = int(input("Số phần muốn cắt (mặc định là 3): ") or 3)
    except ValueError:
        num_segments = 3

    # Process images
    print("\nBắt đầu xử lý ảnh...")
    batch_process_images(input_folder, output_folder, num_segments)
    print(f"\nĐã hoàn thành! Các ảnh đã được lưu vào: {output_folder}")