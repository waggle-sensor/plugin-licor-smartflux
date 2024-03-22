FROM waggle/plugin-base:1.1.1-base
RUN apt-get update && apt-get install -y sshpass
COPY requirements.txt /app/

RUN pip3 install --no-cache-dir --upgrade -r /app/requirements.txt
COPY app /app/

RUN echo "Ciphers aes128-cbc" >> /etc/ssh/ssh_config
WORKDIR /app
ENTRYPOINT ["python3", "/app/app.py"]
