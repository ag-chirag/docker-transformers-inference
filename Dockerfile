FROM public.ecr.aws/sam/build-python3.10:1.135.0-20250310201003

# Set env vars
# Ensures logs output immediately (no buffering)
ENV PYTHONUNBUFFERED=1  
# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1  

# Set working directory
WORKDIR /app

# Amazon Linux uses yum instead of apt-get
# Install curl for healthcheck
RUN yum check-update || true && \
    yum install -y curl && \
    yum clean all && \
    rm -rf /var/cache/yum

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Healthcheck 
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/ping || exit 1

# Set entrypoint - works in both environments
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8080", "--log-level", "info", "--workers", "1", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app.main:app"]