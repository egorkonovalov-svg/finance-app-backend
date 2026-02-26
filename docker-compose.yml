services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: fintrack
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 3s
      timeout: 3s
      retries: 5

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/fintrack
      JWT_SECRET: ${JWT_SECRET:-change-me-to-a-random-secret-in-production}
      JWT_ALGORITHM: ${JWT_ALGORITHM:-HS256}
      JWT_ACCESS_TOKEN_EXPIRE_MINUTES: ${JWT_ACCESS_TOKEN_EXPIRE_MINUTES:-60}
      ENVIRONMENT: ${ENVIRONMENT:-local}
      SMTP_HOST: ${SMTP_HOST:-smtp.gmail.com}
      SMTP_PORT: ${SMTP_PORT:-587}
      SMTP_USER: ${SMTP_USER:-}
      SMTP_PASSWORD: ${SMTP_PASSWORD:-}
      SMTP_FROM_EMAIL: ${SMTP_FROM_EMAIL:-}
      VERIFICATION_CODE_EXPIRE_MINUTES: ${VERIFICATION_CODE_EXPIRE_MINUTES:-10}
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
