# 语音智能匹配系统 (VoiceSync)

## 项目简介 (Project Overview)

### 中文描述
语音智能匹配系统是一款基于云服务的先进语音处理平台，利用AWS服务实现高精度语音转写和文本匹配。系统支持实时语音录制、转录和智能文本分析，为语音识别和文本处理提供全面解决方案。

### English Description
VoiceSync is an advanced cloud-powered voice processing platform that leverages AWS services for high-precision speech transcription and text matching. The system supports real-time voice recording, transcription, and intelligent text analysis, providing a comprehensive solution for voice recognition and text processing.

## Docker构建与部署详细指南 (Docker Build and Deployment Guide)

### 前端镜像构建 (Frontend Image Build)

#### 构建步骤 (Build Steps)
```bash
# 进入前端目录 (Enter frontend directory)
cd frontend

# 构建Docker镜像 (Build Docker Image)
docker build -t voice-matching-frontend:latest .

# 构建带版本标签的镜像 (Build Image with Version Tag)
docker build -t voice-matching-frontend:v1.0.0 .
```

#### Dockerfile解析 (Dockerfile Breakdown)
```dockerfile
# Stage 1: Build
FROM node:18-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code and build
COPY . .
RUN npm run build

# Stage 2: Production with Nginx
FROM nginx:alpine

# Copy built static files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx configuration
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 后端镜像构建 (Backend Image Build)

#### 构建步骤 (Build Steps)
```bash
# 进入后端目录 (Enter backend directory)
cd backend

# 构建Docker镜像 (Build Docker Image)
docker build -t voice-matching-backend:latest .

# 构建带版本标签的镜像 (Build Image with Version Tag)
docker build -t voice-matching-backend:v1.0.0 .
```

#### Dockerfile解析 (Dockerfile Breakdown)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 运行容器 (Running Containers)

#### 前端容器 (Frontend Container)
```bash
# 运行前端容器 (Run Frontend Container)
docker run -p 80:80 voice-matching-frontend:latest
```

#### 后端容器 (Backend Container)
```bash
# 运行后端容器 (Run Backend Container)
docker run -p 8000:8000 \
    -e AWS_ACCESS_KEY_ID=your_access_key \
    -e AWS_SECRET_ACCESS_KEY=your_secret_key \
    -e AWS_DEFAULT_REGION=us-west-2 \
    voice-matching-backend:latest
```

### Docker Compose部署 (Docker Compose Deployment)

#### 环境变量配置 (Environment Variables)
创建 `.env` 文件在项目根目录:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
```

#### Docker Compose配置解析 (Docker Compose Configuration)
```yaml
version: '3.8'

services:
  frontend:
    build: 
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    environment:
      - VITE_BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    networks:
      - voice-matching-network

  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-west-2}
    volumes:
      - ./backend:/app  # 开发模式下的代码热重载
    networks:
      - voice-matching-network

networks:
  voice-matching-network:
    driver: bridge
```

#### 部署命令 (Deployment Commands)
```bash
# 构建并启动服务 (Build and Start Services)
docker-compose up --build

# 后台运行 (Run in Background)
docker-compose up -d --build

# 停止服务 (Stop Services)
docker-compose down

# 查看日志 (View Logs)
docker-compose logs -f
```

### 开发模式说明 (Development Mode Notes)

1. 后端开发 (Backend Development)
- 后端服务使用卷挂载 (`./backend:/app`)，支持代码热重载
- 修改代码后服务会自动重启

2. 前端开发 (Frontend Development)
- 在开发模式下建议直接使用本地开发环境：
```bash
cd frontend
npm install
npm run dev
```

### 镜像管理 (Image Management)

#### 查看和清理 (View and Clean)
```bash
# 查看所有容器 (List Containers)
docker ps -a

# 查看所有镜像 (List Images)
docker images

# 清理未使用的镜像 (Clean Unused Images)
docker image prune -a

# 清理所有未使用的资源 (Clean All Unused Resources)
docker system prune
```

### Kubernetes (EKS) 部署 (Kubernetes Deployment)

[Previous Kubernetes deployment section remains unchanged...]

## 贡献指南 (Contributing)
1. Fork仓库
2. 创建功能分支
3. 实施更改
4. 提交包含详细描述的拉取请求

## 许可证 (License)
MIT License
