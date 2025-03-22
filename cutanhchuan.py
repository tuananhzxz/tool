import os
import cv2
import numpy as np


def detect_main_content_in_segment(segment):
    """
    Detect main content within a single image segment
    """
    # Convert to grayscale
    gray = cv2.cvtColor(segment, cv2.COLOR_BGR2GRAY)

    # Apply adaptive thresholding for better content detection
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # If no contours found, return the original segment
    if not contours:
        return segment

    # Sort contours by area
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # Get bounding box of largest meaningful contour
    x, y, w, h = cv2.boundingRect(contours[0])

    # Add some padding
    padding = 20
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(segment.shape[1] - x, w + 2 * padding)
    h = min(segment.shape[0] - y, h + 2 * padding)

    # Crop segment to main content
    cropped = segment[y:y + h, x:x + w]

    return cropped


def split_and_save_image(image_path, output_folder, num_segments=7):
    """
    Split image into segments, extract main content, and save
    """
    # Read image
    img = cv2.imread(image_path)

    # Get image dimensions
    height, width = img.shape[:2]

    # Calculate segment height
    segment_height = height // num_segments

    # Create output folder if not exists
    os.makedirs(output_folder, exist_ok=True)

    # Get base filename
    base_filename = os.path.splitext(os.path.basename(image_path))[0]

    # Process each segment
    processed_segments = []
    for i in range(num_segments):
        # Calculate segment coordinates
        start_y = i * segment_height
        end_y = start_y + segment_height if i < num_segments - 1 else height

        # Extract segment
        segment = img[start_y:end_y, :]

        # Detect and crop main content in segment
        cropped_segment = detect_main_content_in_segment(segment)

        # Generate output filename with zero-padded numbering
        output_filename = f"{base_filename}_{i + 1:02d}.jpg"
        output_path = os.path.join(output_folder, output_filename)

        # Save segment
        cv2.imwrite(output_path, cropped_segment)
        print(f"Saved segment: {output_filename}")

        processed_segments.append(cropped_segment)

    return processed_segments


def batch_split_images(input_folder, output_folder, num_segments=7):
    """
    Process batch of images in a folder
    """
    # Create output folder if not exists
    os.makedirs(output_folder, exist_ok=True)

    # Process each image
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
            input_path = os.path.join(input_folder, filename)

            try:
                # Split and save image segments
                split_and_save_image(input_path, output_folder, num_segments)
                print(f'Processed: {filename}')
            except Exception as e:
                print(f'Error processing {filename}: {e}')


# Main execution
if __name__ == "__main__":
    input_folder = input("Enter input image folder: ").strip()
    output_folder = input("Enter output folder for segmented images: ").strip()

    # Optional: Allow user to specify number of segments
    try:
        num_segments = int(input("Number of segments (default 7): ") or 7)
    except ValueError:
        num_segments = 7

    batch_split_images(input_folder, output_folder, num_segments)
    print(f"All images have been segmented and saved to: {output_folder}")
    print("Thank you for using the image segmentation tool!")
