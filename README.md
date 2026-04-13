# FastAPI Bookstore API

A REST API for a bookstore built with **FastAPI**, deployable on **AWS EC2** and **AWS Lambda** with **DynamoDB** persistence.

## Architecture

```
Client HTTP
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  API Gateway │────▶│   Mangum     │────▶│   FastAPI    │────▶│  DynamoDB    │
│  (HTTP API)  │     │  (Adapter)   │     │    App       │     │  (books)     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Welcome message |
| `GET` | `/random-book` | Returns a random book |
| `GET` | `/list-books` | Lists all books |
| `GET` | `/book_by_index/{index}` | Get a book by its index |
| `POST` | `/add-book` | Add a new book |
| `GET` | `/get-book?book_id=` | Get a book by its ID |

## Requirements

- Python 3.12+
- Docker (for Lambda packaging)
- AWS account with access to Lambda, API Gateway, and DynamoDB

## Local Development

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Visit http://127.0.0.1:8000/docs for the Swagger UI.

## Deploying to AWS EC2

### 1. Create an EC2 instance

Create an EC2 instance (`t2.micro`) using Amazon Linux 2023 AMI. Open ports **22** (SSH) and **80** (HTTP) in the Security Group.

### 2. Connect via SSH

```bash
ssh -i "your-key.pem" ec2-user@<YOUR_EC2_IP>
```

> **Note:** For Amazon Linux use `ec2-user`. For Ubuntu AMI use `ubuntu`.

### 3. Install dependencies

For **Amazon Linux 2023**:

```bash
sudo dnf update -y
sudo dnf install -y python3-pip nginx git
```

For **Ubuntu**:

```bash
sudo apt-get update
sudo apt install -y python3-pip nginx
```

### 4. Clone and install

```bash
git clone https://github.com/pixegami/fastapi-tutorial.git
cd fastapi-tutorial
pip3 install -r requirements.txt
```

### 5. Configure Nginx

Create the config file:

- **Amazon Linux**: `sudo nano /etc/nginx/conf.d/fastapi.conf`
- **Ubuntu**: `sudo nano /etc/nginx/sites-enabled/fastapi_nginx`

Content (replace with your EC2 public IP):

```nginx
server {
    listen 80;
    server_name <YOUR_EC2_IP>;
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### 6. Start services

```bash
sudo systemctl start nginx
sudo systemctl enable nginx
cd ~/fastapi-tutorial
python3 -m uvicorn main:app
```

To keep it running after closing SSH:

```bash
nohup python3 -m uvicorn main:app &
```

## Deploying to AWS Lambda + DynamoDB

### 1. Create DynamoDB table

In the AWS Console:
- **Table name**: `books`
- **Partition key**: `book_id` (String)

### 2. Create Lambda function

- **Function name**: `fastapi-bookstore`
- **Runtime**: Python 3.12
- **Handler**: `main.handler`
- **Timeout**: 30 seconds (Configuration → General configuration)

### 3. Assign DynamoDB permissions

In the Lambda function's execution role (IAM), attach the policy **AmazonDynamoDBFullAccess**.

### 4. Build the deployment package

Use Docker with the official Lambda image to ensure Linux-compatible binaries:

```bash
# Clean previous build
rm -rf lambda_package/*
rm -f lambda_deployment.zip

# Install dependencies with Docker
docker run --rm --entrypoint pip \
  -v "$(pwd):/app" -w /app \
  public.ecr.aws/lambda/python:3.12 \
  install -r requirements.txt -t lambda_package

# Copy application files
cp main.py lambda_package/

# Create ZIP
cd lambda_package
zip -r ../lambda_deployment.zip .
```

On **Windows (PowerShell)**, use Python to create the ZIP:

```powershell
# Clean
Remove-Item lambda_package\* -Recurse -Force
Remove-Item lambda_deployment.zip -ErrorAction SilentlyContinue

# Install with Docker
docker run --rm --entrypoint pip -v "${PWD}:/app" -w /app public.ecr.aws/lambda/python:3.12 install -r requirements.txt -t lambda_package

# Copy app files
Copy-Item main.py lambda_package\

# Create ZIP with Python
cd lambda_package
python -c "import zipfile, os; z=zipfile.ZipFile('../lambda_deployment.zip','w',zipfile.ZIP_DEFLATED); [z.write(os.path.join(r,f), os.path.relpath(os.path.join(r,f),'.')) for r,d,fs in os.walk('.') for f in fs]; z.close()"
```

### 5. Upload and configure API Gateway

1. Upload `lambda_deployment.zip` to Lambda (Code → Upload from → .zip file)
2. Add trigger → **API Gateway** → **HTTP API** → Security: Open
3. Configure routes in API Gateway:
   - `ANY /` → Lambda integration
   - `ANY /{proxy+}` → Lambda integration
4. Deploy to the `default` stage

### 6. Test

```
https://<API_ID>.execute-api.<REGION>.amazonaws.com/default/list-books
https://<API_ID>.execute-api.<REGION>.amazonaws.com/default/docs
```

### Key configuration in `main.py`

```python
app = FastAPI(root_path="/default")
handler = Mangum(app, api_gateway_base_path="/default")
```

- `root_path="/default"` — tells FastAPI about the stage prefix so Swagger UI works correctly
- `api_gateway_base_path="/default"` — tells Mangum to strip the stage prefix before routing