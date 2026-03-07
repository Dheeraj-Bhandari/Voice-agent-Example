# LiveKit Self-Hosted Voice Agent Platform

Production-ready, self-hosted AI voice calling platform on AWS EC2 with PostgreSQL and Redis.

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           AWS EC2 Instance                                  │
│                                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Redis   │  │ Postgres │  │ LiveKit  │  │   SIP    │  │  Agent   │    │
│  │  :6379   │  │  :5432   │  │  :7880   │  │  :5060   │  │          │    │
│  └──────────┘  └──────────┘  └──────────┘  └────┬─────┘  └──────────┘    │
│                                                 │                         │
│  ┌──────────────────┐  ┌──────────────────┐    │                         │
│  │  RedisInsight    │  │     pgAdmin      │    │                         │
│  │     :5540        │  │      :8080       │    │                         │
│  └──────────────────┘  └──────────────────┘    │                         │
└────────────────────────────────────────────────┼─────────────────────────┘
                                                 │
                                        ┌────────▼────────┐
                                        │   Vobiz.ai      │
                                        │  (SIP Provider) │
                                        └────────┬────────┘
                                                 │ PSTN
                                              📱 Phone
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| LiveKit Server | 7880 | WebRTC server |
| LiveKit SIP | 5060 | SIP-to-WebRTC bridge |
| Redis | 6379 | Caching & state |
| PostgreSQL | 5432 | Database |
| pgAdmin | 8080 | Database UI |
| RedisInsight | 5540 | Redis UI |

## Quick Start

### 1. Launch EC2 Instance

- **AMI**: Ubuntu 24.04 LTS
- **Type**: t3.medium (or t2.micro for testing)
- **Storage**: 20GB

### 2. Configure Security Group

| Port | Protocol | Description |
|------|----------|-------------|
| 22 | TCP | SSH |
| 7880 | TCP | LiveKit API |
| 7881 | TCP | ICE/TCP |
| 5060 | UDP | SIP |
| 8080 | TCP | pgAdmin |
| 5540 | TCP | RedisInsight |
| 10000-20000 | UDP | SIP RTP |
| 50000-60000 | UDP | WebRTC |

### 3. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
exit  # Re-login
```

### 4. Deploy

```bash
mkdir -p ~/livekit/agent && cd ~/livekit

# Create docker-compose.yml (see below)
# Copy agent files to ~/livekit/agent/

docker compose up -d
```

### 5. Create SIP Trunk

```bash
# Install CLI
curl -sSL https://get.livekit.io/cli | bash
export PATH=$PATH:$HOME/.local/bin

# Set credentials
export LIVEKIT_URL=http://localhost:7880
export LIVEKIT_API_KEY=APIAwsKey
export LIVEKIT_API_SECRET=YOUR_SECRET

# Create trunk
lk sip outbound create \
  --address "YOUR_VOBIZ_DOMAIN.sip.vobiz.ai:5060" \
  --numbers "+91XXXXXXXXXX" \
  --auth-user "livekit" \
  --auth-pass "YOUR_PASSWORD" \
  --name "vobiz-outbound"
```

### 6. Make a Call

```bash
docker compose run --rm make-call +919988536242
```

## Files Structure

```
~/livekit/
├── docker-compose.yml    # All services
├── trunk.json            # SIP trunk config
└── agent/
    ├── Dockerfile
    ├── requirements.txt
    ├── agent.py          # AI voice agent
    └── make_call.py      # Call initiator
```

## docker-compose.yml

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: livekit-redis
    network_mode: host
    command: redis-server --bind 0.0.0.0
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    container_name: livekit-postgres
    environment:
      POSTGRES_USER: oktivo
      POSTGRES_PASSWORD: oktivo123
      POSTGRES_DB: oktivo_calls
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@oktivo.com
      PGADMIN_DEFAULT_PASSWORD: admin123
    ports:
      - "8080:80"
    restart: unless-stopped

  livekit-server:
    image: livekit/livekit-server:latest
    container_name: livekit-server
    network_mode: host
    environment:
      LIVEKIT_CONFIG: |
        port: 7880
        keys:
          APIAwsKey: YOUR_API_SECRET
        redis:
          address: localhost:6379
        rtc:
          port_range_start: 50000
          port_range_end: 60000
          tcp_port: 7881
          use_external_ip: true
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
        api_secret: YOUR_API_SECRET
        ws_url: ws://localhost:7880
        redis:
          address: localhost:6379
        sip_port: 5060
        rtp_port: 10000-20000
        use_external_ip: true
    depends_on:
      - livekit-server
    restart: unless-stopped

  agent:
    build: ./agent
    container_name: livekit-agent
    network_mode: host
    environment:
      LIVEKIT_URL: ws://localhost:7880
      LIVEKIT_API_KEY: APIAwsKey
      LIVEKIT_API_SECRET: YOUR_API_SECRET
      SIP_OUTBOUND_TRUNK_ID: ST_xxxxx
      LIVEKIT_AGENT_NAME: outbound-agent
      DATABASE_URL: postgresql://oktivo:oktivo123@localhost:5432/oktivo_calls
    depends_on:
      - livekit-server
      - postgres
    restart: unless-stopped

  make-call:
    build: ./agent
    network_mode: host
    environment:
      LIVEKIT_URL: http://localhost:7880
      LIVEKIT_API_KEY: APIAwsKey
      LIVEKIT_API_SECRET: YOUR_API_SECRET
      SIP_OUTBOUND_TRUNK_ID: ST_xxxxx
      LIVEKIT_AGENT_NAME: outbound-agent
    profiles: [tools]
    entrypoint: ["python", "make_call.py"]

volumes:
  postgres_data:
```

## Web UIs

| Service | URL | Credentials |
|---------|-----|-------------|
| pgAdmin | http://YOUR_IP:8080 | admin@oktivo.com / admin123 |
| RedisInsight | http://YOUR_IP:5540 | Connect to localhost:6379 |

## Vobiz Setup

1. Create account at https://console.vobiz.ai
2. Create Outbound Trunk → Get SIP Domain
3. Add Credentials (username/password)
4. Create matching trunk in LiveKit

## Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f agent

# Make call
docker compose run --rm make-call +919988536242

# Make call with custom context
docker compose run --rm make-call +919988536242 \
  --caller "John" --company "Acme" --purpose "demo"

# Restart agent after code changes
docker compose up -d --build agent

# List SIP trunks
lk sip outbound list
```

## Scaling

- **Horizontal**: Add more agent containers
- **Database**: PostgreSQL handles call logs, leads, analytics
- **Caching**: Redis for session state and real-time data
- **Load Balancer**: Add nginx/ALB for multiple instances

## Cost Estimate (AWS)

| Resource | Monthly |
|----------|---------|
| t3.medium EC2 | ~$30 |
| Elastic IP | Free (attached) |
| Data transfer | ~$5-10 |
| **Total** | ~$35-40 |
