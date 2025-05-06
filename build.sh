#!/usr/bin/env bash

# Update the package list
apt-get update

# Install ffmpeg (required by whisper for audio decoding)
apt-get install -y ffmpeg
