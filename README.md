# 声音匹配测试应用程序 (Voice Matching Test Application)

## 项目概述 (Project Overview)
基于AWS服务的声音转文字和文本匹配应用程序，专为EKS (Elastic Kubernetes Service) 部署优化。

### 主要特性 (Key Features)
- 实时语音录制与转录 (Real-time Voice Recording and Transcription)
- AWS Transcribe语音转文字 (AWS Transcribe Speech-to-Text)
- AWS Bedrock文本匹配 (AWS Bedrock Text Matching)
- S3音频文件存储 (S3 Audio File Storage)
- 安全的IAM角色服务账户认证 (Secure IAM Role-based Service Account Authentication)

## EKS部署先决条件 (EKS Deployment Prerequisites)

### 环境准备 (Environment Preparation)
1. AWS账户 (AWS Account)
2. EKS集群 (EKS Cluster)
3. 安装工具 (Required Tools):
   - AWS CLI (v2+)
   - eksctl
   - kubectl
   - Docker

### 安全配置 (Security Configuration)

#### 1. 创建IAM策略 (Create IAM Policy)
```bash
# 创建后端服务IAM策略 (Create Backend Service IAM Policy)
aws iam create-policy \
    --policy-name VoiceMatchingBackendPolicy \
    --policy-document file://k8s/iam-policy.json
```

#### 2. 配置OIDC提供者 (Configure OIDC Provider)
```bash
# 为EKS集群启用OIDC提供者 (Enable OIDC Provider for EKS Cluster)
eksctl utils associate-iam-oidc-provider \
    --cluster=your-cluster-name \
    --approve
```

#### 3. 创建IAM服务账户 (Create IAM Service Account)
```bash
# 替换${ACCOUNT_ID}为您的AWS账户ID (Replace ${ACCOUNT_ID} with your AWS Account ID)
eksctl create iamserviceaccount \
    --cluster=your-cluster-name \
    --namespace=default \
    --name=voice-matching-backend-sa \
    --attach-policy-arn=arn:aws:iam::${ACCOUNT_ID}:policy/VoiceMatchingBackendPolicy \
    --approve
```

### 部署步骤 (Deployment Steps)

#### 1. 构建容器镜像 (Build Container Images)
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

#### 2. 部署到EKS (Deploy to EKS)
```bash
# 部署AWS负载均衡控制器 (Deploy AWS Load Balancer Controller)
kubectl apply -f k8s/alb-controller.yaml

# 部署后端和前端服务 (Deploy Backend and Frontend Services)
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

## AWS服务集成 (AWS Service Integrations)

### 支持的服务 (Supported Services)
- AWS Transcribe: 语音转文字
- AWS Bedrock: 使用Claude模型的文本匹配
- AWS S3: 音频文件存储与检索

### IAM权限详解 (IAM Permissions Breakdown)
- `transcribe:*`: 完全访问转录作业
- `bedrock:InvokeModel`: 调用Bedrock模型的能力
- `s3:GetObject`, `s3:ListBucket`: S3存储桶读取权限

## 性能优化 (Performance Tuning)

### 推荐的EKS集群配置 (Recommended EKS Cluster Configuration)
- 节点组: 至少2个节点 (At least 2 nodes)
- 实例类型: m5.large 或更高 (m5.large or better)
- 自动扩展: 启用 (Auto Scaling: Enabled)
- 存储: GP3 EBS卷 (GP3 EBS volumes)

## 监控 (Monitoring)
- 启用CloudWatch容器洞察 (Enable CloudWatch Container Insights)
- 设置AWS X-Ray进行分布式追踪 (Set up AWS X-Ray for distributed tracing)
- 使用EKS控制平面日志记录 (Use EKS Control Plane Logging)

## 故障排除 (Troubleshooting)

### 常见EKS部署问题 (Common EKS Deployment Issues)
1. OIDC提供者未配置 (OIDC Provider Not Configured)
   - 确保运行 `eksctl utils associate-iam-oidc-provider`
   
2. IAM角色绑定失败 (IAM Role Binding Failures)
   - 验证策略ARN
   - 检查账户ID
   - 确认集群名称

3. 服务账户权限 (Service Account Permissions)
   - 使用 `kubectl describe sa voice-matching-backend-sa` 验证注解

## 安全建议 (Security Recommendations)
- 使用最小权限原则 (Use Least Privilege Principle)
- 定期轮换IAM凭证 (Regularly Rotate IAM Credentials)
- 启用网络策略 (Enable Network Policies)
- 使用私有子网 (Use Private Subnets)

## 贡献指南 (Contributing)
1. Fork仓库
2. 创建功能分支
3. 实施更改
4. 提交包含详细描述的拉取请求

## 许可证 (License)
MIT License
