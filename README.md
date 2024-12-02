# VoiceSync

## Project Overview

VoiceSync is an advanced cloud-powered voice processing platform that leverages AWS services for high-precision speech transcription and text matching. The system supports real-time voice recording, transcription, and intelligent text analysis, providing a comprehensive solution for voice recognition and text processing.

### System Workflow

1. Start: The user initiates the system.
2. Input AWS Credentials: The user enters their AWS credentials.
3. Validate Credentials: The system checks if the provided credentials are valid.
   - If invalid, the process returns to the input step.
   - If valid, the process continues.
4. Input the System Prompt
5. Choose Input Method: The user selects one of two input methods:
   - Real-time audio recording
   - S3 file upload
6. Audio Input: Based on the user's choice, one of the following actions is performed:
   - Record real-time audio, or
   - Upload an audio file to S3
7. Transcribe Audio: The system transcribes the audio input into text.
8. Bedrock Inference: The transcribed text is processed using AWS Bedrock for inference.
9. Display Results: The system displays the results of the transcription and inference.

This workflow covers the main functionalities of the VoiceSync system, including user authentication, flexible audio input methods, audio transcription, AI-based inference, and result presentation.

## Docker Deployment Guide

### Local Development Deployment

1. Create Environment Variables
```bash
# Create .env file
cat > .env << EOL
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
BACKEND_URL=http://backend:8000/api
EOL
```

2. Build and Start Services
```bash
docker-compose up --build
```

3. Access Application
- Frontend: http://localhost:8080
- Backend: http://localhost:8000/api

### Cloud Deployment

1. Create Environment Variables with Backend URL
```bash
# Create .env file
cat > .env << EOL
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
# Use ALB address
BACKEND_URL=https://your-alb-address.com/api
EOL
```

2. Build and Start Services
```bash
docker-compose up --build
```

3. Configure ALB
   - Add a listener rule for HTTPS (port 443), with the default rule pointing to the EC2 deployment on port 80
   - Set a new rule to forward requests with the path pattern `/api/*` to the backend service (EC2 instance port 8000)
   - Ensure that the EC2 security group (80/8000) is open to the ALB security group
   - Ensure that the ALB security group has port 443 open

4. Access Application
   - Frontend: https://your-alb-address.com
   - Backend: https://your-alb-address.com/api

### Configuration Notes

1. Backend URL Configuration
   - Local development: Default is http://backend:8000/api
   - Cloud deployment: Set via BACKEND_URL environment variable, should include the `/api` prefix

2. AWS Credentials Configuration
   - AWS_ACCESS_KEY_ID: AWS access key ID
   - AWS_SECRET_ACCESS_KEY: AWS secret access key
   - AWS_DEFAULT_REGION: AWS region (default: us-west-2)

3. Backend API Prefix
   - All backend API routes are prefixed with `/api`
   - For example, the credential validation endpoint is `/api/validate_credentials`

### Project Structure
```
.
├── frontend/                      # Vue.js frontend application
│   ├── src/                      # Source code
│   ├── public/                   # Static assets
│   └── Dockerfile               # Frontend Docker configuration
├── backend/                      # Python backend service
│   ├── main.py                  # Main application
│   └── Dockerfile               # Backend Docker configuration
└── docker-compose.yml           # Docker Compose configuration
```

### Common Issues

1. Connection Error
```
Error: net::ERR_CONNECTION_REFUSED
```
Solution:
- Local development: Ensure backend service is running
- Cloud deployment: Verify BACKEND_URL configuration, ensure it includes the `/api` prefix

2. AWS Credentials Error
```
Invalid credentials
```
Solution:
- Check AWS credentials in the .env file
- Ensure AWS credentials have necessary permissions

3. Mixed Content Error
If you see mixed content errors on an HTTPS site, ensure all requests (including backend API calls) use HTTPS.

## Development Considerations

1. Backend API Routes
   All backend API routes are prefixed with `/api`. When developing new API endpoints, there's no need to include `/api` in the route definition as it's already set globally in the FastAPI application.

2. Frontend API Calls
   Ensure all API calls to the backend use the correct URL, including the `/api` prefix. This is typically configured through the `BACKEND_URL` environment variable.

3. Local Development vs Production
   - For local development, the backend URL is typically `http://backend:8000/api`
   - In production, it should be a complete HTTPS URL, e.g., `https://your-domain.com/api`

## Contributing
1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Submit a pull request with a detailed description

## License
MIT License
