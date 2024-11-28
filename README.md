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

### Kubernetes (EKS) 部署 (Kubernetes Deployment)

#### 先决条件 (Prerequisites)
1. AWS账户 (AWS Account)
2. EKS集群 (EKS Cluster)
3. 安装工具 (Required Tools):
   - AWS CLI (v2+)
   - eksctl
   - kubectl
   - Docker

#### 安全配置 (Security Configuration)

##### 1. 创建IAM策略 (Create IAM Policy)
```bash
# 创建后端服务IAM策略 (Create Backend Service IAM Policy)
aws iam create-policy \
    --policy-name VoiceMatchingBackendPolicy \
    --policy-document file://k8s/iam-policy.json
```

##### 2. 配置OIDC提供者 (Configure OIDC Provider)
```bash
# 为EKS集群启用OIDC提供者 (Enable OIDC Provider for EKS Cluster)
eksctl utils associate-iam-oidc-provider \
    --cluster=your-cluster-name \
    --approve
```

##### 3. 创建IAM服务账户 (Create IAM Service Account)
```bash
# 替换${ACCOUNT_ID}为您的AWS账户ID (Replace ${ACCOUNT_ID} with your AWS Account ID)
eksctl create iamserviceaccount \
    --cluster=your-cluster-name \
    --namespace=default \
    --name=voice-matching-backend-sa \
    --attach-policy-arn=arn:aws:iam::${ACCOUNT_ID}:policy/VoiceMatchingBackendPolicy \
    --approve
```

#### 部署步骤 (Deployment Steps)

##### 1. 构建容器镜像 (Build Container Images)
```bash
# 后端镜像 (Backend Image)
aws ecr create-repository --repository-name voice-matching-backend
docker build -t ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/voice-matching-backend:latest backend
aws ecr get-login-password | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com
docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/voice-matching-backend:latest

# 前端镜像 (Frontend Image)
aws ecr create-repository --repository-name voice-matching-frontend
docker build -t ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/voice-matching-frontend:latest frontend
docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/voice-matching-frontend:latest
```

##### 2. 部署到EKS (Deploy to EKS)
```bash
# 部署AWS负载均衡控制器 (Deploy AWS Load Balancer Controller)
kubectl apply -f k8s/alb-controller.yaml

# 部署后端和前端服务 (Deploy Backend and Frontend Services)
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

## 贡献指南 (Contributing)
1. Fork仓库
2. 创建功能分支
3. 实施更改
4. 提交包含详细描述的拉取请求

## 许可证 (License)
MIT License
