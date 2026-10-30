# Deployment image for Render (free tier) / Railway / Fly / any Docker host. See DEPLOY.md.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# Regenerate the demo documents inside the image so the build never depends on binary files in git / LFS.
RUN useradd -m appuser && python make_samples.py && chown -R appuser /app
USER appuser

EXPOSE 8501
# Render / Railway inject $PORT; locally it falls back to 8501. GROQ_API_KEY (or GEMINI_API_KEY) comes from the host's env settings.
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
