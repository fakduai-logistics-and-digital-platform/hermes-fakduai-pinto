# Hermes + Pinto Docker

<img width="1536" alt="image" src="https://github.com/user-attachments/assets/6e9f5963-74b3-402b-a385-5a3112d3329a" />


This project builds a Hermes Agent Docker image with the Pinto Chat adapter plugin included.

## What Is Included

- Hermes Agent (Python, installed via pip)
- Pinto adapter plugin from [pinto-adapter-hermes](https://github.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes)
- Cloudflare tunnel support (Quick Tunnel or named tunnel)
- Webhook and API port: `8642`
- Config folder: `./hermes-config`

## 1. เตรียม `.env`

```bash
cp .env.example .env
```

แก้ `.env` ตั้ง API Server Key:

```bash
# สร้าง key
sh scripts/generate-api-key.sh
```

ใส่ key ใน `.env`:

```text
API_SERVER_KEY=your-generated-key
PINTO_BOT_ID=your-pinto-bot-id
```

หรือรัน setup script อัตโนมัติ:

```bash
sh scripts/configure-domain.sh
```

## 2. Build Image

**Docker:**
```bash
docker compose build
```

**Podman:**
```bash
podman-compose build
```

## 3. Start Local Hermes

**Docker:**
```bash
docker compose up -d
```

**Podman:**
```bash
podman-compose up -d
```

ตรวจสอบ:
```bash
curl http://127.0.0.1:8642/
# {"status":"ok","platform":"hermes-agent",...}
```

Webhook health:
```bash
curl http://127.0.0.1:8642/plugins/pinto/webhook
# {"ok":true,"channel":"pinto"}
```

## 4. Use Cloudflare Quick Tunnel

Quick Tunnel สำหรับ testing — URL เปลี่ยนทุกครั้งที่ restart

**Docker:**
```bash
docker compose -f docker-compose.yml -f docker-compose.trycloudflare.yml up -d
```

**Podman:**
```bash
podman-compose -f docker-compose.yml -f docker-compose.trycloudflare.yml up -d
```

ดู URL ที่สร้าง:

```bash
docker compose -f docker-compose.yml -f docker-compose.trycloudflare.yml logs -f cloudflared
```

ตัวอย่าง output:
```text
https://something-random.trycloudflare.com
```

ใช้:
```text
Web UI:   https://something-random.trycloudflare.com/
Webhook:  https://something-random.trycloudflare.com/plugins/pinto/webhook
```

⚠️ อย่ารัน `down` ถ้าไม่อยากได้ URL ใหม่

## 5. Use Cloudflare With Your Domain (แนะนำ)

ใน Cloudflare Zero Trust:

1. **Networks > Tunnels** → Create tunnel
2. เลือก **Cloudflared**
3. เลือก **Docker**
4. Copy token หลัง `--token`
5. เพิ่ม Public Hostname เช่น `hermes.example.com`
6. Service type: **HTTP**
7. Service URL:

```text
hermes-gateway:8642
```

แก้ `.env`:

```text
CLOUDFLARE_TUNNEL_TOKEN=your-token
PINTO_WEBHOOK_URL=https://hermes.example.com/plugins/pinto/webhook
```

Start:

**Docker:**
```bash
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d
```

**Podman:**
```bash
podman-compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d
```

ใช้:
```text
Web UI:   https://hermes.example.com/
Webhook:  https://hermes.example.com/plugins/pinto/webhook
```

## 6. Configure Pinto

ตั้งค่า Bot ใน Pinto App:

- `Bot ID`: bot UUID ของคุณ
- `Webhook URL`: URL จากข้อ 4 หรือ 5 + `/plugins/pinto/webhook`
- `Webhook Secret`: ตรงกับ `PINTO_WEBHOOK_SECRET` ใน `.env`

ทดสอบ webhook:

```bash
curl -i https://your-domain.example.com/plugins/pinto/webhook
```

Expected:
```json
{"ok":true,"channel":"pinto"}
```

## Common Commands

ดู container ที่รันอยู่:
```bash
docker compose ps
```

ดู gateway logs:
```bash
docker compose logs -f hermes-gateway
```

ดู Cloudflare logs:
```bash
docker compose -f docker-compose.yml -f docker-compose.trycloudflare.yml logs -f cloudflared
```

รัน Hermes CLI:
```bash
docker compose run --rm hermes-cli config
docker compose run --rm hermes-cli tools list
docker compose run --rm hermes-cli status
```

Shell เข้า container:
```bash
docker compose run --rm --entrypoint sh hermes-cli
```

Restart gateway:
```bash
docker compose restart hermes-gateway
```

หยุด:
```bash
docker compose down
```

## Podman Commands

ถ้าใช้ Podman แทน Docker — เปลี่ยน `docker compose` เป็น `podman-compose`:

```bash
podman-compose build
podman-compose up -d
podman-compose logs -f hermes-gateway
podman-compose down
```

หรือใช้ `podman` โดยตรง:

```bash
podman build -t hermes-pinto:local .
podman run -d --name hermes -p 8642:8642 -v ./hermes-config:/root/.hermes hermes-pinto:local
```

## Reset

Reset API key:
1. แก้ `.env`
2. เปลี่ยน `API_SERVER_KEY`
3. Rebuild:

```bash
docker compose build
docker compose up -d
```

Reset config ทั้งหมด:

```bash
docker compose down
rm -rf hermes-config
docker compose up -d
```

Full clean rebuild:

```bash
docker compose down
rm -rf hermes-config
docker compose build --no-cache
docker compose up -d
```

## Troubleshooting

### Webhook ไม่ตอบ

ตรวจสอบ:
```bash
docker compose logs --tail=50 hermes-gateway
```

### `Pinto plugin not found`

Plugin ไม่ถูกติดตั้ง —  rebuild:
```bash
docker compose build --no-cache
docker compose up -d
```

### `Unable to reach the origin service`

Cloudflare รันอยู่แต่ Hermes ไม่ listen ที่ 8642:

```bash
docker compose ps
docker compose logs --tail=100 hermes-gateway
docker compose restart hermes-gateway
```

### Quick Tunnel URL เปลี่ยน

เป็นเรื่องปกติ — Quick Tunnel URLs เป็นแบบชั่วคราว

อัปเดต:
- Pinto webhook URL

สำหรับ URL คงที่ ใช้ named Cloudflare Tunnel กับ domain ของคุณเอง

## File Structure

```
hermes-pinto-docker/
├── Dockerfile                          # Hermes + Pinto plugin image
├── docker-compose.yml                  # Main compose (gateway + cli)
├── docker-compose.cloudflare.yml       # Named Cloudflare Tunnel overlay
├── docker-compose.trycloudflare.yml    # Quick Tunnel overlay
├── .env.example                        # Environment template
├── .dockerignore
├── .gitignore
├── LICENSE
├── README.md                           # This file
└── scripts/
    ├── docker-entrypoint.sh            # Container entrypoint
    ├── bootstrap-hermes-config.py      # Auto-configure Hermes
    ├── configure-domain.sh             # Interactive setup script
    └── generate-api-key.sh             # Generate API_SERVER_KEY
```

## Related

- **Adapter Plugin:** [pinto-adapter-hermes](https://github.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes)
- **Hermes Agent:** [hermes-agent](https://github.com/NousResearch/hermes-agent)
- **OpenClaw Pattern:** [openclaw-fakduai-pinto](https://github.com/jatura-fakduai/openclaw-fakduai-pinto)

## Author

**Theeraphat S** ([@Theeraphat-S](https://github.com/Theeraphat-S))

## License

MIT
