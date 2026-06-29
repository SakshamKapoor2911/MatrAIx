# syntax=docker/dockerfile:1.7
#
# Docker Linux CUA stack for persona-computer-1 (Harbor Computer1 runtime):
# Xvfb + xfwm4 + Chromium + xfce4-terminal + xdotool/imagemagick/webp tooling.

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        curl \
        dbus-x11 \
        fonts-liberation \
        imagemagick \
        procps \
        python3 \
        scrot \
        webp \
        wmctrl \
        x11-utils \
        xauth \
        xdotool \
        xfce4-session \
        xfce4-terminal \
        xfwm4 \
        xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && chmod 1777 /tmp /var/tmp \
    && mkdir -p /tmp/.ICE-unix && chmod 1777 /tmp/.ICE-unix \
    && mkdir -p /logs /app/input /app/output /root/.config/xfce4/helpers \
    && chmod 777 /logs /app/input /app/output \
    && printf '%s\n' \
        '[Desktop Entry]' \
        'Version=1.0' \
        'Encoding=UTF-8' \
        'Name=Terminal Emulator' \
        'Exec=xfce4-terminal' \
        'Icon=utilities-terminal' \
        'Type=Application' \
        'Terminal=false' \
        > /root/.config/xfce4/helpers/custom-TerminalEmulator.desktop

WORKDIR /app
