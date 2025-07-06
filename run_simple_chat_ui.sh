#!/bin/bash

# Build and run the simple chat UI with Docker Compose

echo "🚀 Starting Simple Temporal Flow Chat UI..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build and start the chat UI service
echo "📦 Building simple chat UI container..."
docker-compose --profile ui build chat-ui

echo "🎯 Starting simple chat UI service..."
docker-compose --profile ui up -d chat-ui

# Wait a moment for the service to start
sleep 5

# Check if the service is running
if docker-compose ps chat-ui | grep -q "Up"; then
    echo "✅ Simple Chat UI is running successfully!"
    echo "🌐 Open your browser and navigate to: http://localhost:3000"
    echo ""
    echo "🔥 This is the simplified implementation with:"
    echo "   - AI SDK 5 Beta integration"
    echo "   - Basic streaming chat interface"
    echo "   - Temporal workflow focus"
    echo "   - No database required"
    echo ""
    echo "📊 You can also access:"
    echo "   - Temporal UI: http://localhost:8080"
    echo "   - Temporal Server: localhost:7233"
    echo ""
    echo "🆚 Compare with the full reference: ./run_chat_ui.sh"
    echo "🛑 To stop the chat UI, run: docker-compose --profile ui down chat-ui"
else
    echo "❌ Failed to start chat UI. Check logs with: docker-compose logs chat-ui"
    exit 1
fi
