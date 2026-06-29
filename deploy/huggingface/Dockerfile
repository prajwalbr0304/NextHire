# HuggingFace Space (Docker SDK) — runs the prebuilt image published to GHCR by
# the GitHub Actions workflow (.github/workflows/deploy-web.yml). The image must
# be PUBLIC on GHCR for the Space to pull it without authentication.
#
# This thin wrapper inherits the base image's USER (uid 1000), EXPOSE 7860 and
# CMD (uvicorn serving the API + the exported Next.js UI), so nothing else is
# needed here. To pull the latest build, use the Space's "Factory rebuild".
FROM ghcr.io/prajwalbr0304/nexthire:latest

EXPOSE 7860
