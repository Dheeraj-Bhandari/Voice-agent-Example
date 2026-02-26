# LiveKit Outbound Voice Agent

A minimal Docker-based AI voice agent that makes outbound phone calls using LiveKit + Vobiz (or Twilio).

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐
│   make_call.py   │────▶│   LiveKit Cloud  │────▶│  Vobiz.ai    │────▶ 📱 Phone
│  (dispatch call) │     │   (AI Agent)     │ SIP │ (SIP trunk)  │ PSTN
└──────────────────┘     └──────────────────┘     └──────────────┘
```

## Prerequisites

1. **LiveKit Cloud** account - https://cloud.livekit.io
2. **Vobiz.ai** account - https://console.vobiz.ai (or Twilio)
3. **Docker** installed

## Quick Setup

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. LiveKit Setup

1. Go to https://cloud.livekit.io
2. Create a project and get:
   - `LIVEKIT_URL` (wss://your-project.livekit.cloud)
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET` (Settings > Keys > Create key)

### 3. Vobiz Setup (Recommended)

1. Go to https://console.vobiz.ai
2. Create a SIP trunk → Get the **SIP Domain** (e.g., `xxxxx.sip.vobiz.ai`)
3. Configure **Credentials** on the trunk (username/password)
4. Get a phone number

### 4. Create Outbound Trunk in LiveKit

Go to LiveKit Dashboard > Telephony > SIP Trunks > Create new trunk > **Outbound**:

| Field | Value |
|-------|-------|
| Address | `your-trunk-id.sip.vobiz.ai` |
| Numbers | Your Vobiz phone number |
| Username | Your Vobiz trunk username |
| Password | Your Vobiz trunk password |

Copy the **Trunk ID** (ST_xxx) to your `.env` file.

## Running

### Start the agent

```bash
docker compose up --build
```

### Make a call

```bash
# Basic call
docker compose run --rm make-call +919988536242

# With custom context
docker compose run --rm make-call +919988536242 --caller "John" --company "Acme Inc" --purpose "demo"
```

## Project Structure

```
├── agent.py          # AI voice agent (STT → LLM → TTS)
├── make_call.py      # Script to initiate outbound calls
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Configuration

See `.env.example` for all configuration options.

## Twilio Alternative

Twilio can be used instead of Vobiz, but free trial has SIP trunk limitations. For Twilio:

1. Create Elastic SIP Trunk with Termination credentials
2. Update LiveKit trunk with `your-trunk.pstn.twilio.com`

Note: Twilio trial requires upgrading ($20+) for full SIP trunk support.

## Troubleshooting

- **No call received**: Check agent logs with `docker compose logs agent`
- **Call disconnects immediately**: Verify SIP trunk credentials match between LiveKit and Vobiz
- **Agent not responding**: Ensure LiveKit API keys are correct
