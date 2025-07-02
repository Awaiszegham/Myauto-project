# YouTube Dubbing AI Agent - Redesigned

A comprehensive Python-based system for automatically dubbing YouTube videos into different languages using Google Gemini CLI for AI processing and advanced bot detection mitigation strategies.

## 🚀 Key Features

- **Google Gemini CLI Integration**: Leverages the latest Gemini CLI for transcription and translation
- **Advanced Bot Detection Mitigation**: Sophisticated strategies to avoid YouTube's bot detection
- **Pure Python Architecture**: Simplified, maintainable codebase without external workflow tools
- **100% Accuracy Testing**: Comprehensive testing framework focused on accuracy measurement
- **Scalable Design**: Built for both personal use and enterprise deployment
- **Secure & Private**: Temporary file processing with automatic cleanup

## 🏗️ Architecture Overview

The system consists of several key components:

- **Flask API**: RESTful API for managing dubbing requests and status
- **Celery Workers**: Asynchronous task processing for long-running operations
- **Redis**: Message broker and result backend
- **Gemini CLI Service**: Interface to Google Gemini CLI for AI operations
- **YouTube Service**: Video download with bot detection mitigation
- **Audio Service**: Audio processing and text-to-speech using AWS Polly

## 📋 Prerequisites

- Python 3.11+
- Redis server
- FFmpeg
- Google Gemini CLI (installed and configured)
- AWS credentials (for text-to-speech)
- YouTube API credentials (for uploads)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd youtube_dubbing_ai_redesigned
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install system dependencies**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install ffmpeg redis-server
   
   # macOS
   brew install ffmpeg redis
   ```

5. **Install and configure Gemini CLI**:
   ```bash
   # Follow instructions from: https://github.com/google-gemini/gemini-cli
   # Ensure the CLI is in your PATH and properly authenticated
   ```

6. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# AWS Configuration (for Polly TTS)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1

# YouTube API Configuration
YOUTUBE_API_KEY=your-youtube-api-key
YOUTUBE_CREDENTIALS_FILE=path/to/youtube_credentials.json

# Bot Detection Mitigation
PROXY_URL=http://your-proxy-server:port  # Optional
YOUTUBE_COOKIES_FILE=path/to/cookies.txt  # Optional

# Gemini CLI Configuration
GEMINI_API_KEY=your-gemini-api-key
```

### YouTube Cookies (Recommended)

To improve download reliability, export cookies from your browser:

1. **Using browser extension**: Install a cookie export extension
2. **Export cookies**: Export YouTube cookies to a text file
3. **Configure path**: Set `YOUTUBE_COOKIES_FILE` in your `.env`

## 🚀 Quick Start

1. **Start Redis server**:
   ```bash
   redis-server
   ```

2. **Start Celery worker** (in a new terminal):
   ```bash
   source venv/bin/activate
   celery -A src.routes.dubbing:celery worker --loglevel=info
   ```

3. **Start Flask application** (in another terminal):
   ```bash
   source venv/bin/activate
   python src/main.py
   ```

4. **Test the system**:
   ```bash
   curl http://localhost:5000/api/dubbing/health
   ```

## 📖 API Usage

### Start Dubbing Process

```bash
curl -X POST http://localhost:5000/api/dubbing/start-dubbing \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "target_language": "es",
    "source_language": "en"
  }'
```

### Check Task Status

```bash
curl http://localhost:5000/api/dubbing/task-status/TASK_ID
```

### List All Tasks

```bash
curl http://localhost:5000/api/dubbing/tasks
```

### Get Supported Languages

```bash
curl http://localhost:5000/api/dubbing/supported-languages
```

## 🧪 Testing

The system includes a comprehensive testing framework designed for 100% accuracy:

### Run All Tests

```bash
python run_tests.py
```

### Run Specific Test Categories

```bash
# Test Gemini CLI integration
python run_tests.py --category gemini

# Test YouTube service
python run_tests.py --category youtube

# Test audio processing
python run_tests.py --category audio

# Test complete integration
python run_tests.py --category integration
```

### Run Integration Tests

```bash
# Requires actual API credentials
python run_tests.py --integration
```

### Test Output

The test runner provides detailed accuracy metrics:

- Overall accuracy percentage
- Component-specific success rates
- Failure analysis and recommendations
- Performance benchmarks
- Detailed JSON reports

## 🔧 Bot Detection Mitigation

The system implements several strategies to avoid YouTube's bot detection:

### 1. User-Agent Rotation
- Randomly selects from a pool of realistic browser user-agents
- Mimics different browsers and operating systems

### 2. Intelligent Delays
- Random delays between requests (1-3 seconds)
- Simulates human browsing patterns

### 3. Proxy Support
- Configurable proxy routing
- Distributes requests across multiple IP addresses

### 4. Cookie Authentication
- Uses browser cookies for authenticated requests
- Appears as logged-in user activity

### 5. HTTP Header Optimization
- Mimics real browser headers
- Includes Accept, Accept-Language, and other standard headers

### 6. Retry Logic
- Exponential backoff for failed requests
- Intelligent error handling and recovery

## 📊 Monitoring and Logging

### Application Logs

The system provides detailed logging for monitoring:

```python
# Configure logging level in .env
DEBUG=True  # For detailed logs
```

### Task Monitoring

Monitor Celery tasks:

```bash
# View active tasks
celery -A src.routes.dubbing:celery inspect active

# View task stats
celery -A src.routes.dubbing:celery inspect stats
```

### Database Monitoring

Check task status in the database:

```python
from src.models.video_task import VideoTask
tasks = VideoTask.query.all()
```

## 🚀 Deployment

### Local Development

```bash
# Start all services locally
python src/main.py
```

### Docker Deployment

```bash
# Build image
docker build -t youtube-dubbing-ai .

# Run with docker-compose
docker-compose up -d
```

### Cloud Deployment

The system supports deployment on various cloud platforms:

- **Railway.com**: One-click deployment with automatic scaling
- **Heroku**: Easy deployment with worker dynos
- **AWS**: Full control with EC2, ECS, or Lambda
- **Google Cloud**: Integration with Google services

## 🔒 Security Best Practices

### Credential Management
- Store API keys in environment variables
- Use secure credential files for OAuth tokens
- Rotate keys regularly

### Data Protection
- Automatic cleanup of temporary files
- Encrypted data transmission (HTTPS)
- Minimal data retention

### Access Control
- Implement authentication for production use
- Use rate limiting for API endpoints
- Monitor for unusual activity

## 🐛 Troubleshooting

### Common Issues

1. **Gemini CLI not found**:
   ```bash
   # Ensure Gemini CLI is installed and in PATH
   which gemini
   gemini --version
   ```

2. **YouTube download failures**:
   ```bash
   # Update yt-dlp
   pip install --upgrade yt-dlp
   
   # Check cookies file
   ls -la $YOUTUBE_COOKIES_FILE
   ```

3. **Redis connection errors**:
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Restart Redis
   sudo systemctl restart redis-server
   ```

4. **AWS Polly errors**:
   ```bash
   # Verify AWS credentials
   aws sts get-caller-identity
   
   # Test Polly access
   aws polly describe-voices --region us-east-1
   ```

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=True
python src/main.py
```

### Log Analysis

Check application logs for errors:

```bash
tail -f app.log
```

## 📈 Performance Optimization

### Scaling Workers

Increase Celery workers for better performance:

```bash
# Run multiple workers
celery -A src.routes.dubbing:celery worker --concurrency=4
```

### Memory Optimization

Configure memory limits for large videos:

```python
# In your .env
MAX_VIDEO_SIZE_MB=500
MAX_AUDIO_DURATION_MINUTES=60
```

### Storage Optimization

Use cloud storage for better performance:

```env
# Configure Cloudflare R2
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=your-bucket-name
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run pre-commit hooks
pre-commit install

# Run tests before committing
python run_tests.py
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Gemini team for the CLI and AI capabilities
- yt-dlp developers for the robust YouTube download library
- AWS Polly for high-quality text-to-speech
- Flask and Celery communities for excellent frameworks

## 📞 Support

For support and questions:

- Create an issue on GitHub
- Check the troubleshooting guide
- Review the test results for accuracy metrics

---

**Version**: 2.0.0  
**Last Updated**: January 2025  
**Author**: Manus AI

