#!/bin/bash

# Name des Binaries
BINARY_NAME="fileenc"

# Zielplattformen und Architekturen
PLATFORMS=("linux" "windows")
ARCHITECTURES=("amd64" "arm64")

# Ausgabeverzeichnis
OUTPUT_DIR="./build"
mkdir -p "$OUTPUT_DIR"

# Build für jede Plattform und Architektur
for PLATFORM in "${PLATFORMS[@]}"; do
  for ARCH in "${ARCHITECTURES[@]}"; do
    OUTPUT_NAME="$BINARY_NAME-$PLATFORM-$ARCH"
    
    # Füge .exe für Windows hinzu
    if [ "$PLATFORM" == "windows" ]; then
      OUTPUT_NAME="$OUTPUT_NAME.exe"
    fi

    echo "Building $PLATFORM/$ARCH..."
    GOOS="$PLATFORM" GOARCH="$ARCH" go build -o "$OUTPUT_DIR/$OUTPUT_NAME" .
    
    # Fehlerprüfung
    if [ $? -ne 0 ]; then
      echo "Build failed for $PLATFORM/$ARCH"
      exit 1
    fi
  done
done

echo "Builds completed successfully. Binaries are in the '$OUTPUT_DIR' directory."
