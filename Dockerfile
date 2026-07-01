FROM node:20-bookworm-slim

# Install system dependencies, Python, pip, Google Chrome and its driver dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    wget \
    curl \
    gnupg \
    ca-certificates \
    apt-transport-https \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb --no-install-recommends \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
RUN pip3 install selenium beautifulsoup4 webdriver-manager --break-system-packages

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy application source code
COPY . .

# Build the Next.js app
RUN npm run build

# Expose port (Hugging Face Spaces expects port 7860 by default)
ENV PORT 7860
EXPOSE 7860

# Start command
CMD ["npm", "start"]
