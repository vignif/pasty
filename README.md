<p align="center">
  <img src="static/logo.png" alt="Logo" width="200"/>
</p>

## Pasty: copy and paste online
A simple online clipboard to easily move text between two machines connected to the internet.
When you save your text you will get a unique identifier of it.
To retrieve your text just use the identifier.
A simple FastAPI-based application to store and retrieve short text snippets using SQLite. This project demonstrates how to use FastAPI for building a web API with basic CRUD operations and background tasks.

![Tests](https://github.com/vignif/pasty/actions/workflows/test.yml/badge.svg)

[![Demo](https://img.shields.io/badge/Demo-online-blue?logo=fastapi)](https://ntrolci.onrender.com/)

![Coverage](https://img.shields.io/codecov/c/github/vignif/pasty/main)

## Features
- **Store Text**: Submit text via a web form or JSON API.
- **Retrieve Text**: Retrieve text content by unique ID.
- **Expiration Handling**: Text entries expire after a configurable period, and expired entries are automatically deleted in the background.
- **Concurrency**: Supports simultaneous submissions and ensures unique ID generation.

## Requirements
- Python 3.7+
- FastAPI
- SQLite
- `python-dotenv` (for environment variable management)

## Setup

1. **Clone the repository:**
  ```bash
  git clone https://github.com/vignif/pasty.git
  cd pasty
  ```

2. **Create and activate a virtual environment:**
  ```bash
  python3 -m venv venv_ntrol
  source venv_ntrol/bin/activate
  ```

3. **Install dependencies:**
  ```bash
  pip install -r requirements.txt
  ```

4. **Set environment variables:**
  Create a `.env` file in the root directory and set variables as needed:
  ```env
  EXPIRATION_HOURS=12
  DATABASE_URL=sqlite:///store.db
  ```

## Usage

### Local Development

Run the FastAPI app locally:
```bash
uvicorn main:app --reload --port 6001
```
Access the web UI at [http://localhost:6001](http://localhost:6001).

### Docker

Build and run with Docker:
```bash
docker build -t pasty .
docker run -p 6001:6001 pasty
```

### Netlify

Serverless functions are in the `api/` directory. See `netlify.toml` for configuration.

## API Endpoints

- `POST /save` — Save text, returns unique ID
- `GET /get/{id}` — Retrieve text by ID
- `GET /api/count` — Get current row count

## Testing

Run tests with pytest:
```bash
pytest --cov=.
```

## Deployment

- **Docker:** See `Dockerfile` and `docker-compose.yml` for container setup.
- **Netlify:** See `netlify.toml` for serverless deployment.
- **Other:** Can be deployed on any platform supporting FastAPI and SQLite.

## Contributing

Pull requests and issues are welcome! Please add tests for new features.

## License

See `LICENSE.md` for details.
