FROM python:3.11-slim

LABEL description="SovereignForge code execution sandbox — isolated, no network"

# Install common scientific/utility libraries
RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    pandas==2.2.2 \
    matplotlib==3.9.0 \
    scipy==1.13.1 \
    Pillow==10.4.0 \
    sympy==1.12 \
    requests==2.32.3

# Create unprivileged sandbox user — NEVER run as root
RUN useradd -m -u 1000 sandboxuser
USER sandboxuser

WORKDIR /sandbox

# Verify the sandbox is working
RUN python3 -c "import numpy, pandas, matplotlib; print('sandbox: deps OK')"

CMD ["python3", "-c", "print('sandbox ready')"]
