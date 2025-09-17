FROM apache/beam_python3.11_sdk:2.57.0


WORKDIR /opt/app
COPY beam_app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


COPY beam_app/ ./
ENTRYPOINT ["python", "-m", "main"]