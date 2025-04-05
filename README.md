# Finance NLP Chatbot

This project is a finance-focused NLP chatbot that integrates real-time data, financial news, and various NLP capabilities.

## Directory Structure
- **api_gateway/**: The FastAPI application that orchestrates requests.
- **data_service/**: Module for fetching stock/crypto prices.
- **news_service/**: Service for ingesting and retrieving financial news.
- **scraper_service/**: Service for scraping and summarizing web content.
- **prediction_service/**: (Optional) Module for price prediction.

## Setup Instructions
1. Install Docker and Docker Compose.
2. Run `docker-compose up --build` from the root directory.
3. Access the API at `http://localhost:8000`.

## Development
- The project uses FastAPI for the backend.
- Each service has its own Dockerfile for containerization.
