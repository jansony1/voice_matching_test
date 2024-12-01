FROM node:18-alpine as builder

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm install

# 复制源代码
COPY . .

# 构建生产版本 - 这会生成静态文件到 dist 目录
RUN npm run build

# 生产环境 - 使用nginx服务静态文件
FROM nginx:alpine

# 从构建阶段复制编译好的静态文件
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx配置
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
