# 语音智能匹配系统 (VoiceSync)

## 项目简介 (Project Overview)

### 中文描述
语音智能匹配系统是一款基于云服务的先进语音处理平台，利用AWS服务实现高精度语音转写和文本匹配。系统支持实时语音录制、转录和智能文本分析，为语音识别和文本处理提供全面解决方案。

### English Description
VoiceSync is an advanced cloud-powered voice processing platform that leverages AWS services for high-precision speech transcription and text matching. The system supports real-time voice recording, transcription, and intelligent text analysis, providing a comprehensive solution for voice recognition and text processing.

## Docker部署指南 (Docker Deployment Guide)

### 本地开发部署 (Local Development Deployment)

1. 创建环境变量文件 (Create Environment Variables)
```bash
# Create .env file
cat > .env << EOL
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
EOL
```

2. 构建并启动服务 (Build and Start Services)
```bash
docker-compose up --build
```

3. 访问应用 (Access Application)
- 前端界面 (Frontend): http://localhost:8080
- 后端服务 (Backend): http://localhost:8000

### 云端部署 (Cloud Deployment)

1. 创建环境变量文件，添加后端服务地址 (Create Environment Variables with Backend URL)
```bash
# Create .env file
cat > .env << EOL
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
# 使用EC2公网地址或ALB地址 (Use EC2 public IP or ALB address)
BACKEND_URL=http://your-ec2-ip:8000
EOL
```

2. 构建并启动服务 (Build and Start Services)
```bash
docker-compose up --build
```

3. 访问应用 (Access Application)
- 前端界面 (Frontend): http://your-server-ip:8080
- 后端服务 (Backend): http://your-server-ip:8000

### 配置说明 (Configuration Notes)

1. 后端URL配置 (Backend URL Configuration)
- 本地开发：默认使用 http://backend:8000 (Local Development: Default to http://backend:8000)
- 云端部署：通过 BACKEND_URL 环境变量设置 (Cloud Deployment: Set via BACKEND_URL environment variable)

2. AWS凭证配置 (AWS Credentials Configuration)
- AWS_ACCESS_KEY_ID: AWS访问密钥ID
- AWS_SECRET_ACCESS_KEY: AWS访问密钥
- AWS_DEFAULT_REGION: AWS区域 (默认: us-west-2)

### 目录结构 (Project Structure)
```
.
├── frontend/                      # Vue.js前端应用
│   ├── src/                      # 源代码
│   ├── public/                   # 静态资源
│   └── Dockerfile               # 前端Docker配置
├── backend/                      # Python后端服务
│   ├── main.py                  # 主应用
│   └── Dockerfile               # 后端Docker配置
└── docker-compose.yml           # Docker Compose配置
```

### 常见问题 (Common Issues)

1. 连接错误 (Connection Error)
```
Error: net::ERR_CONNECTION_REFUSED
```
解决方案 (Solution):
- 本地开发：确保后端服务正常运行 (Local: Ensure backend service is running)
- 云端部署：检查 BACKEND_URL 配置是否正确 (Cloud: Verify BACKEND_URL configuration)

2. AWS凭证错误 (AWS Credentials Error)
```
Invalid credentials
```
解决方案 (Solution):
- 检查 .env 文件中的 AWS 凭证是否正确 (Check AWS credentials in .env file)
- 确保 AWS 凭证具有必要的权限 (Ensure AWS credentials have necessary permissions)

## 贡献指南 (Contributing)
1. Fork仓库
2. 创建功能分支
3. 实施更改
4. 提交包含详细描述的拉取请求

## 许可证 (License)
MIT License
