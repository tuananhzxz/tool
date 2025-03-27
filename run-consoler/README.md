# Image Processing Tools

Bộ công cụ xử lý ảnh với các chức năng:
- Chuyển đổi định dạng ảnh (JPEG, PNG, WebP)
- Cắt và ghép ảnh
- Tải ảnh từ web
- Gộp file Word
- Đổi tên ảnh

## Yêu cầu hệ thống

- Python 3.7 trở lên
- Các thư viện trong file requirements.txt

## Cài đặt

1. Clone repository này về máy:
```bash
git clone <repository_url>
cd image_splitter
```

2. Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

## Sử dụng

1. Chạy ứng dụng:
```bash
python app.py
```

2. Mở trình duyệt và truy cập: http://localhost:5000

3. Chọn chức năng cần sử dụng:

### Chuyển đổi định dạng ảnh
- Hỗ trợ chuyển đổi giữa các định dạng JPEG, PNG và WebP
- Có thể tải lên nhiều ảnh cùng lúc
- Kết quả được nén thành file ZIP để tải về

### Cắt và ghép ảnh
- Cắt ảnh: Cắt một ảnh thành nhiều phần theo chiều dọc
- Ghép ảnh: Ghép nhiều ảnh thành một ảnh theo chiều dọc
- Có thể điều chỉnh kích thước ảnh trước khi xử lý
- Kết quả được nén thành file ZIP để tải về

### Tải ảnh từ web
- Tải ảnh từ bất kỳ trang web nào
- Hỗ trợ đặc biệt cho các trang webtoon:
  + Hiển thị danh sách chapter
  + Tải ảnh từ chapter được chọn
- Kết quả được nén thành file ZIP để tải về

### Gộp file Word
- Gộp nhiều file Word thành một file duy nhất
- Giữ nguyên định dạng văn bản
- Kết quả được nén thành file ZIP để tải về

### Đổi tên ảnh
- Đổi tên hàng loạt các file ảnh theo số thứ tự
- Kết quả được nén thành file ZIP để tải về

## Lưu ý

- Kích thước file tải lên tối đa là 16MB
- Các file tạm thời sẽ được xóa sau khi xử lý xong
- Nên tải về kết quả ngay sau khi xử lý xong
