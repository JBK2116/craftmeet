# Set the python base image
FROM python:3.14-slim

# Install UV for venv management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set /app/ as the working directory
WORKDIR /app

# Use copied files instead of hardlinks in venv
ENV UV_LINK_MODE=copy

# Copy venv dependencies into app
COPY pyproject.toml uv.lock ./

# Install all production dependencies
RUN uv sync --frozen --no-dev

# Copy remaining backend source code into /app/
COPY . ./

# Enable execution of startup script
RUN chmod +x entrypoint.sh

# Expose port 8000 for requests
EXPOSE 8000

# Start the backend server on port 8000
CMD ["./entrypoint.sh"]
