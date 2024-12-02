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
BACKEND_URL=http://backend:8000/api
EOL
```

2. 构建并启动服务 (Build and Start Services)
```bash
docker-compose up --build
```

3. 访问应用 (Access Application)
- 前端界面 (Frontend): http://localhost:8080
- 后端服务 (Backend): http://localhost:8000/api

### 云端部署 (Cloud Deployment)

1. 创建环境变量文件，添加后端服务地址 (Create Environment Variables with Backend URL)
```bash
# Create .env file
cat > .env << EOL
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
# 使用ALB地址 (Use ALB address)
BACKEND_URL=https://your-alb-address.com/api
EOL
```

2. 构建并启动服务 (Build and Start Services)
```bash
docker-compose up --build
```

3. 配置ALB (Configure ALB)
   - 为HTTPS（443端口）添加一个监听器规则
   - 将路径模式为 `/api/*` 的请求转发到后端服务（EC2实例的8000端口）

4. 访问应用 (Access Application)
   - 前端界面 (Frontend): https://your-alb-address.com
   - 后端服务 (Backend): https://your-alb-address.com/api

### 配置说明 (Configuration Notes)

1. 后端URL配置 (Backend URL Configuration)
   - 本地开发：默认使用 http://backend:8000/api
   - 云端部署：通过 BACKEND_URL 环境变量设置，应包含 `/api` 前缀

2. AWS凭证配置 (AWS Credentials Configuration)
   - AWS_ACCESS_KEY_ID: AWS访问密钥ID
   - AWS_SECRET_ACCESS_KEY: AWS访问密钥
   - AWS_DEFAULT_REGION: AWS区域 (默认: us-west-2)

3. 后端API前缀 (Backend API Prefix)
   - 所有后端API路由都以 `/api` 为前缀
   - 例如，验证凭证的端点为 `/api/validate_credentials`

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
- 云端部署：检查 BACKEND_URL 配置是否正确，确保包含 `/api` 前缀 (Cloud: Verify BACKEND_URL configuration, ensure it includes the `/api` prefix)

2. AWS凭证错误 (AWS Credentials Error)
```
Invalid credentials
```
解决方案 (Solution):
- 检查 .env 文件中的 AWS 凭证是否正确 (Check AWS credentials in .env file)
- 确保 AWS 凭证具有必要的权限 (Ensure AWS credentials have necessary permissions)

3. 混合内容错误 (Mixed Content Error)
如果在HTTPS网站上看到混合内容错误，确保所有请求（包括后端API调用）都使用HTTPS。

## 开发注意事项 (Development Considerations)

1. 后端API路由 (Backend API Routes)
   所有后端API路由都以 `/api` 为前缀。在开发新的API端点时，无需在路由定义中包含 `/api`，因为它已经在 FastAPI 应用程序中全局设置。

2. 前端API调用 (Frontend API Calls)
   确保所有对后端的API调用都使用正确的URL，包括 `/api` 前缀。这通常通过 `BACKEND_URL` 环境变量来配置。

3. 本地开发与生产环境 (Local Development vs Production)
   - 本地开发时，后端URL通常是 `http://backend:8000/api`
   - 在生产环境中，它应该是完整的HTTPS URL，例如 `https://your-domain.com/api`

## 贡献指南 (Contributing)
1. Fork仓库
2. 创建功能分支
3. 实施更改
4. 提交包含详细描述的拉取请求

## 许可证 (License)
MIT License
