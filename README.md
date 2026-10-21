# Sentiment Pulse

An AI-powered social media sentiment dashboard. It classifies posts as **Positive**, **Negative** or **Neutral** with a self-trained model, stores every prediction, caches repeated requests, and summarises the results on a dashboard.

> 🚧 Work in progress. Full documentation (setup, API examples, metrics, design decisions, limitations) will be added as each part lands.

## Stack

| Layer | Technology |
|---|---|
| Data & ML | Python, pandas, scikit-learn (TF-IDF + Logistic Regression) |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Cache | Redis |
| Frontend | Next.js, TypeScript, Tailwind CSS, Recharts |
| Deployment | Docker Compose (local), Render (API), Vercel (frontend) |
