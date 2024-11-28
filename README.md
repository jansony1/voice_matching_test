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
# 基础镜像 (Base Image)
FROM node:18-alpine

# 工作目录 (Working Directory)
WORKDIR /app

# 复制依赖文件 (Copy Dependency Files)
COPY package*.json ./

# 安装依赖 (Install Dependencies)
RUN npm install

# 复制所有源代码 (Copy Source Code)
COPY . .

# 构建应用 (Build Application)
RUN npm run build

# 暴露端口 (Expose Port)
EXPOSE 5173

# 启动命令 (Start Command)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
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
# 基础镜像 (Base Image)
FROM python:3.11-slim

# 工作目录 (Working Directory)
WORKDIR /app

# 安装系统依赖 (Install System Dependencies)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件 (Copy Dependency Files)
COPY requirements.txt .

# 安装Python依赖 (Install Python Dependencies)
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码 (Copy Application Code)
COPY . .

# 暴露端口 (Expose Port)
EXPOSE 8000

# 启动命令 (Start Command)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 运行容器 (Running Containers)

#### 前端容器 (Frontend Container)
```bash
# 运行前端容器 (Run Frontend Container)
docker run -p 5173:5173 \
    -e VITE_BACKEND_URL=http://backend:8000 \
    voice-matching-frontend:latest
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

#### 环境变量 (Environment Variables)
创建 `.env` 文件:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
```

#### 部署命令 (Deployment Commands)
```bash
# 构建并启动服务 (Build and Start Services)
docker-compose up --build

# 后台运行 (Run in Background)
docker-compose up -d --build

# 停止服务 (Stop Services)
docker-compose down
```

### 镜像管理 (Image Management)

#### 查看本地镜像 (List Local Images)
```bash
docker images
```

#### 删除镜像 (Remove Images)
```bash
# 删除特定镜像 (Remove Specific Image)
docker rmi voice-matching-frontend:latest

# 删除未使用镜像 (Remove Unused Images)
docker image prune
```

## Docker开发注意事项 (Docker Development Considerations)

### 安全建议 (Security Recommendations)
1. 不要在Dockerfile中硬编码敏感信息
2. 使用 `.dockerignore` 排除不必要文件
3. 定期更新基础镜像
4. 最小权限原则
5. 使用多阶段构建减小镜像体积

### 性能优化 (Performance Optimization)
- 选择轻量级基础镜像
- 合理配置资源限制
- 使用卷挂载进行开发调试
- 配置适当的网络模式

### 常见问题排查 (Troubleshooting)

#### 镜像构建问题 (Image Build Issues)
- 检查依赖版本兼容性
- 验证构建上下文
- 查看详细构建日志

#### 容器运行问题 (Container Runtime Issues)
- 检查端口映射
- 验证环境变量
- 查看容器日志 `docker logs <container_id>`

## 持续集成 (Continuous Integration)

### GitHub Actions示例 (GitHub Actions Example)
```yaml
name: Docker CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Build Frontend
      run: docker build ./frontend
    
    - name: Build Backend
      run: docker build ./backend
```

## 贡献指南 (Contributing)
1. Fork仓库
2. 创建功能分支
3. 实施更改
4. 提交包含详细描述的拉取请求

## 许可证 (License)
MIT License
