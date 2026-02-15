# Shelter System — Production Build

## Start (Ubuntu)

```bash
chmod +x install.sh
./install.sh
```

## Manual start

```bash
docker compose up -d --build
docker compose exec backend python init_data.py
```

## Admin
- login: admin
- password: admin123
