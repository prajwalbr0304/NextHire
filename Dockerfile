# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Stage-3 reproduction image for the Redrob Ranker *ranking step*.
#
# CPU-only and fully offline at run time. The committed frozen retrieval index
# (artifacts/) makes the ranking step finish in well under the 5-minute budget.
# candidates.jsonl is the organisers' data: it is MOUNTED at run time and never
# baked into the image (see .dockerignore).
#
#   docker build -t redrob-ranker .
#   docker run --rm --network none \
#     -v /abs/path/candidates.jsonl:/data/candidates.jsonl \
#     -v "$PWD/out":/out \
#     redrob-ranker
#   # -> ./out/submission.csv
# ---------------------------------------------------------------------------
FROM python:3.13-slim

# Deterministic, offline-friendly, unbuffered logs.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# Install pinned dependencies first so this layer is cached across code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project: source + the committed frozen index in artifacts/.
COPY . .

# Mount points for the (run-time) input data and the output directory.
RUN mkdir -p /data /out

# Default = the single documented reproduce command. Override to validate/test:
#   ... redrob-ranker python validate_submission.py /out/submission.csv
#   ... redrob-ranker pytest -q
CMD ["python", "rank.py", "--candidates", "/data/candidates.jsonl", "--out", "/out/submission.csv"]
