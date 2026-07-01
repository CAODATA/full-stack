FROM node:18-bullseye-slim

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
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
RUN pip3 install selenium beautifulsoup4 webdriver-manager

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy application source code
COPY . .

# Build the Next.js app
RUN npm run build

# Expose port (Next.js start will honor PORT env variable set by cloud hosting like Hugging Face or Render)
ENV PORT 3000
EXPOSE 3000

# Start command
CMD ["npm", "start"]
