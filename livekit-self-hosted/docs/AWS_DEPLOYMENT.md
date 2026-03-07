# AWS EC2 Deployment Guide

Deploy self-hosted LiveKit with SIP on AWS EC2.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AWS EC2 Instance                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │  Redis  │  │ LiveKit │  │   SIP   │  │  Agent  │        │
│  └─────────┘  └─────────┘  └────┬────┘  └─────────┘        │
│                                 │                           │
└─────────────────────────────────┼───────────────────────────┘
                                  │ Elastic IP
                                  ▼
                          ┌───────────────┐
                          │    Vobiz.ai   │
                          └───────┬───────┘
                                  │ PSTN
                                📱 Phone
```

## Step 1: Launch EC2 Instance

### 1.1 Go to AWS Console
- https://console.aws.amazon.com/ec2

### 1.2 Launch Instance
- Click "Launch Instance"
- **Name**: `livekit-server`
- **AMI**: Ubuntu Server 24.04 LTS (or Amazon Linux 2023)
- **Instance Type**: `t3.medium` (recommended) or `t2.micro` (free tier)
- **Key Pair**: Create new or use existing (you'll need this to SSH)

### 1.3 Network Settings
- **VPC**: Default
- **Auto-assign Public IP**: Enable
- **Security Group**: Create new (we'll configure ports next)

### 1.4 Storage
- 20 GB gp3 (default is fine)

### 1.5 Launch
- Click "Launch Instance"

## Step 2: Configure Security Group

Go to EC2 > Security Groups > Select your instance's security group > Edit Inbound Rules

Add these rules:

| Type | Port Range | Source | Description |
|------|------------|--------|-------------|
| SSH | 22 | Your IP | SSH access |
| Custom TCP | 7880 | 0.0.0.0/0 | LiveKit API |
| Custom TCP | 7881 | 0.0.0.0/0 | ICE/TCP |
| Custom UDP | 5060 | 0.0.0.0/0 | SIP Signaling |
| Custom UDP | 10000-20000 | 0.0.0.0/0 | SIP RTP Media |
| Custom UDP | 50000-60000 | 0.0.0.0/0 | WebRTC UDP |

## Step 3: Allocate Elastic IP

**Important**: You need a static IP for SIP to work.

1. Go to EC2 > Elastic IPs
2. Click "Allocate Elastic IP address"
3. Click "Allocate"
4. Select the new IP > Actions > "Associate Elastic IP address"
5. Select your instance
6. Click "Associate"

**Note your Elastic IP** (e.g., `13.234.xx.xx`) - you'll need this for Vobiz configuration.

## Step 4: Connect to Instance

```bash
# Windows (PowerShell)
ssh -i "your-key.pem" ubuntu@YOUR_ELASTIC_IP

# Or use PuTTY on Windows
```

## Step 5: Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Logout and login again for group changes
exit
```

SSH back in after logout.

## Step 6: Deploy LiveKit

```bash
# Create directory
mkdir -p ~/livekit && cd ~/livekit

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
services:
  redis:
    image: redis:7-alpine
    container_name: livekit-redis
    volumes:
      - redis_data:/data
    restart: unless-stopped

  livekit-server:
    image: livekit/livekit-server:latest
    container_name: livekit-server
    network_mode: host
    environment:
      LIVEKIT_CONFIG: |
        port: 7880
        keys:
          APIAwsKey: YOUR_SECRET_HERE_CHANGE_ME
        redis:
          address: localhost:6379
        rtc:
          port_range_start: 50000
          port_range_end: 60000
          tcp_port: 7881
          use_external_ip: true
        logging:
          level: info
    depends_on:
      - redis
    restart: unless-stopped

  livekit-sip:
    image: livekit/sip:latest
    container_name: livekit-sip
    network_mode: host
    environment:
      SIP_CONFIG_BODY: |
        api_key: APIAwsKey
        api_secret: YOUR_SECRET_HERE_CHANGE_ME
        ws_url: ws://localhost:7880
        redis:
          address: localhost:6379
        sip_port: 5060
        rtp_port: 10000-20000
        use_external_ip: true
        logging:
          level: info
    depends_on:
      - livekit-server
    restart: unless-stopped

  agent:
    image: livekit/agents-playground:latest
    container_name: livekit-agent
    network_mode: host
    environment:
      LIVEKIT_URL: ws://localhost:7880
      LIVEKIT_API_KEY: APIAwsKey
      LIVEKIT_API_SECRET: YOUR_SECRET_HERE_CHANGE_ME
    depends_on:
      - livekit-server
    restart: unless-stopped

volumes:
  redis_data:
EOF
```

### Generate a secure API secret:

```bash
# Generate random secret
openssl rand -base64 32
# uTNVhNxW8Rc99b2FHYLz30uO15EP9cZI7U9IbjN1Y6g=
```

**Replace `YOUR_SECRET_HERE_CHANGE_ME`** in docker-compose.yml with the generated secret.

```bash
# Edit the file
nano docker-compose.yml
# Replace YOUR_SECRET_HERE_CHANGE_ME with your generated secret
# Save: Ctrl+O, Enter, Ctrl+X
```

### Start services:

```bash
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## Step 7: Deploy Your Custom Agent

Instead of the playground agent, deploy your Oktivo agent:

```bash
# Create agent directory
mkdir -p ~/livekit/agent && cd ~/livekit/agent

# Create files (copy from your local livekit-self-hosted/agent/)
# Or use scp to copy files from your Windows machine:
```

From your Windows machine:
```powershell
# Copy agent files to EC2
scp -i "your-key.pem" -r .\livekit-self-hosted\agent\* ubuntu@YOUR_ELASTIC_IP:~/livekit/agent/
```

Then on EC2:
```bash
cd ~/livekit

# Update docker-compose.yml to use custom agent
# Replace the agent service with:
```

```yaml
  agent:
    build:
      context: ./agent
      dockerfile: Dockerfile
    container_name: livekit-agent
    network_mode: host
    environment:
      LIVEKIT_URL: ws://localhost:7880
      LIVEKIT_API_KEY: APIAwsKey
      LIVEKIT_API_SECRET: YOUR_SECRET_HERE
      SIP_OUTBOUND_TRUNK_ID: ST_xxxxx  # Add after creating trunk
      LIVEKIT_AGENT_NAME: outbound-agent
    depends_on:
      - livekit-server
    restart: unless-stopped
```

## Step 8: Configure Vobiz

1. Go to https://console.vobiz.ai
2. Edit your SIP trunk
3. Update **Termination URI** to: `YOUR_ELASTIC_IP:5060`
4. Keep credentials same (username: `livekit`, password: `livekit`)

## Step 9: Create SIP Trunk in LiveKit

On your EC2 instance:

```bash
# Install livekit-cli
curl -sSL https://get.livekit.io/cli | bash

# Set environment
export LIVEKIT_URL=http://localhost:7880
export LIVEKIT_API_KEY=APIAwsKey
export LIVEKIT_API_SECRET=YOUR_SECRET_HERE

# Create outbound trunk
livekit-cli sip trunk create \
  --address "2402cfa5.sip.vobiz.ai" \
  --numbers "+911171366938" \
  --username "livekit" \
  --password "livekit"
```

Copy the returned `ST_xxxxx` trunk ID.

## Step 10: Update Agent and Test

```bash
# Update trunk ID in docker-compose.yml
nano docker-compose.yml
# Add SIP_OUTBOUND_TRUNK_ID=ST_xxxxx to agent environment

# Restart
docker compose up -d --build

# Make a test call
docker compose run --rm agent python make_call.py +919988536242
```

## Troubleshooting

### Check if services are running:
```bash
docker compose ps
docker compose logs livekit-sip
```

### Check if ports are open:
```bash
sudo netstat -tuln | grep -E "5060|7880|10000"
```

### Test SIP connectivity:
```bash
# From outside, test if SIP port responds
nc -vuz YOUR_ELASTIC_IP 5060
```

## Cost Estimate

| Resource | Monthly Cost |
|----------|--------------|
| t3.medium EC2 | ~$30 |
| t2.micro (free tier) | $0 (first year) |
| Elastic IP (attached) | $0 |
| Data transfer | ~$5-10 |

## Security Recommendations

1. Use strong API secrets
2. Restrict SSH to your IP only
3. Consider adding HTTPS with Caddy/nginx
4. Enable AWS CloudWatch for monitoring
5. Set up automatic backups
