# Sử dụng một ảnh nền Python gọn nhẹ
FROM python:3.11-slim

# Cập nhật và cài đặt FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Đặt thư mục làm việc bên trong container
WORKDIR /app

# Sao chép file requirements và cài đặt các thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ code còn lại (main.py) vào
COPY . .

# Lệnh để chạy bot khi container khởi động
CMD ["python", "main.py"]