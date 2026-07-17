# Craftmeet

A privacy focused, real time meeting webapp for running structured sessions
and extracting the best ideas from your group.

Craftmeet lets hosts build meetings with a flexible set of question types,
run them live with participants, and walk away with a detailed AI generated
PDF summary of every response.

## Features

- Five question formats: multiple choice, long answer, ranked voting,
  rating scale, and yes/no
- Live meeting rooms via WebSockets
- AI powered PDF summaries using OpenAI
- Real time response streaming for hosts
- No account required for participants
- Privacy focused: no tracking, ads or data selling
- Free and open source

## Tech Stack

| Layer      | Technology             |
| ---------- | ---------------------- |
| Frontend   | SvelteKit (SPA)        |
| Backend    | FastAPI (async)        |
| Database   | PostgreSQL via asyncpg |
| HTTP/HTTPS | Caddy                  |
| Migrations | Alembic                |
| Real time  | WebSockets             |
| AI         | OpenAI API             |
| Testing    | pytest, pytest-asyncio |

### Testing

```bash
cd backend
pytest
```

## Deployment

The frontend is built locally and rsynced to the server to provide fast deployments and updates. Backend and other services run in Docker.

### Prerequisites

- SSH access to the VPS configured
- The VPS has cloned the repo
- The VPS repo has a configured root `.env`
- The VPS repo has configured `backend/.env`

### Backend changes only

```bash
git push
ssh craftmeet "cd ~/craftmeet && git pull && docker compose up -d --build"
```

### Frontend changes (or both)

```bash
git push

cd frontend
npm ci
npm run build
rsync -r build/ craftmeet:~/craftmeet/frontend/build/

ssh craftmeet "cd ~/craftmeet && git pull && docker compose up -d --build"
```

## License

This application is fully open-source. Use it however you need.
