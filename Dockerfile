FROM continuumio/miniconda3

WORKDIR /app

# 환경 정의 먼저 복사
COPY environment.yml .
COPY requirements_gpu.txt .

# Conda 환경 생성
RUN conda env create -f environment.yml

# Node.js & npm 설치 (프론트 실행용)
RUN apt-get update && apt-get install -y default-jdk curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:${PATH}"

# 📦 Chrome 설치
RUN apt-get update && apt-get install -y \
    wget unzip gnupg2 ca-certificates fonts-liberation \
    libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 libnss3 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 xdg-utils \
    libu2f-udev libvulkan1 libgbm1 jq --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable

# 📦 Chromedriver 설치 (자동 버전 매칭)
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') && \
    echo "Detected Chrome version: $CHROME_VERSION" && \
    CHROMEDRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" \
        | jq -r --arg ver "$CHROME_VERSION" '.channels.Stable.version') && \
    echo "Installing Chromedriver version: $CHROMEDRIVER_VERSION" && \
    wget -O /tmp/chromedriver.zip "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /usr/local/bin/chromedriver-linux64

# 이후 SHELL 설정
SHELL ["conda", "run", "-n", "review-app", "/bin/bash", "-c"]

# 미디어파이프 및 grpcio-status 별도 설치 (protobuf 충돌 방지)
RUN pip install mediapipe==0.10.15 grpcio-status==1.56.2

# GPU 의존성 설치
RUN pip install --extra-index-url https://download.pytorch.org/whl/cu118 -r requirements_gpu.txt

# 앱 코드 복사
COPY . /app

# 실행 스크립트 등록
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["conda", "run", "-n", "review-app", "/bin/bash", "/start.sh"]