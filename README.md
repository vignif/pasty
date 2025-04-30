# Pasty

A simple online clipboard to easily move text between two machines connected to the internet.
When you save your text you will get a unique identifier of it.
To retrieve your text just use the identifier.
A simple FastAPI-based application to store and retrieve short text snippets using SQLite. This project demonstrates how to use FastAPI for building a web API with basic CRUD operations and background tasks.

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

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/text-storage-api.git
cd text-storage-api
