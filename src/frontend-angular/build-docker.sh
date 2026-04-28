#!/bin/bash

# Build script for Angular Docker container
set -e

echo "🔨 Building Angular application for production..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/

# Build the Angular application
echo "📦 Building Angular application..."
npm run build --configuration=production

echo "✅ Angular build completed successfully!"

# Build Docker image
echo "🐳 Building Docker image..."
docker build -t aio-ui:latest .

echo "✅ Docker image built successfully!"
echo "🚀 You can now run the container with: docker run -p 4200:80 aio-ui:latest"
