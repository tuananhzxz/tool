import cv2
import pytesseract

# Đọc ảnh
image = cv2.imread("1.jpg")
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Tiền xử lý ảnh
blurred = cv2.GaussianBlur(gray, (5, 5), 0)
_, binary = cv2.threshold(blurred, 128, 255, cv2.THRESH_BINARY_INV)

# Áp dụng morphological operations để làm sạch nền
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

# Phát hiện các contour (bong bóng thoại)
contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Lọc contour theo diện tích tối thiểu
min_area = 10000
speech_bubbles = []
for contour in contours:
    if cv2.contourArea(contour) > min_area:
        x, y, w, h = cv2.boundingRect(contour)
        speech_bubbles.append((x, y, x + w, y + h))  # Lưu tọa độ của bong bóng thoại

# Sử dụng Tesseract OCR để trích xuất văn bản từ toàn bộ ảnh
custom_config = r'--oem 3 --psm 6'
data = pytesseract.image_to_data(cleaned, lang='kor', config=custom_config, output_type=pytesseract.Output.DICT)

# Phân loại và nhóm văn bản
texts_in_bubbles = [[] for _ in range(len(speech_bubbles))]  # Nhóm văn bản theo từng bong bóng thoại
texts_outside = []  # Văn bản ngoài bong bóng thoại

for i in range(len(data['text'])):
    text = data['text'][i].strip()
    if not text:  # Bỏ qua nếu đoạn văn bản rỗng
        continue

    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
    center_x, center_y = x + w // 2, y + h // 2  # Tọa độ tâm của đoạn văn bản

    # Kiểm tra xem đoạn văn bản có nằm trong bất kỳ bong bóng thoại nào không
    in_bubble = False
    for idx, bubble in enumerate(speech_bubbles):
        bubble_x1, bubble_y1, bubble_x2, bubble_y2 = bubble
        if bubble_x1 <= center_x <= bubble_x2 and bubble_y1 <= center_y <= bubble_y2:
            texts_in_bubbles[idx].append(text)  # Thêm vào nhóm tương ứng
            in_bubble = True
            break

    # Nếu không nằm trong bong bóng thoại, thêm vào danh sách ngoài bong bóng thoại
    if not in_bubble:
        texts_outside.append(text)

    # Vẽ khung xanh quanh đoạn văn bản
    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

# Hiển thị kết quả
print("Văn bản trong bong bóng thoại:")
for idx, group in enumerate(texts_in_bubbles, start=1):
    print(f"Bong bóng thoại {idx}: {' '.join(group)}")

print("\nVăn bản ngoài bong bóng thoại:")
print(f"{' '.join(texts_outside)}")

# Hiển thị ảnh với các đoạn văn bản đã phát hiện
cv2.imshow("Detected Text", image)
cv2.waitKey(0)
cv2.destroyAllWindows()