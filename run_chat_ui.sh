#!/bin/bash

# Run the AI Chatbot Reference implementation

echo "🚀 Starting AI Chatbot Reference (AI SDK 5 Beta)..."

# Check if we're in the right directory
if [ ! -f "ai-chatbot-reference/package.json" ]; then
    echo "❌ Please run this script from the temporal_flow_engine root directory"
    exit 1
fi

# Navigate to the ai-chatbot-reference directory
cd ai-chatbot-reference

# Check if pnpm is available
if ! command -v pnpm &> /dev/null; then
    echo "📦 Installing pnpm package manager..."
    npm install -g pnpm
fi

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    pnpm install
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating environment file..."
    cp .env.example .env
    echo "AUTH_SECRET=$(openssl rand -base64 32)" >> .env
    echo "XAI_API_KEY=\${OPENAI_API_KEY}" >> .env
    echo ""
    echo "⚠️  NOTE: This reference implementation includes advanced features that require:"
    echo "   - PostgreSQL database (for user management and chat history)"
    echo "   - Redis (for caching)"
    echo "   - Vercel Blob (for file uploads)"
    echo ""
    echo "   For basic testing, some features will be disabled."
fi

echo "🎯 Starting development server..."
echo "🔍 Looking for available ports (3000, 3001, 3002)..."

# Start the development server
pnpm dev &
DEV_PID=$!

# Wait a moment for the server to start
sleep 8

# Check which port it's running on by testing actual connectivity
if curl -s http://localhost:3002 > /dev/null 2>&1; then
    PORT=3002
elif curl -s http://localhost:3001 > /dev/null 2>&1; then
    PORT=3001
elif curl -s http://localhost:3000 > /dev/null 2>&1; then
    PORT=3000
else
    echo "❌ Failed to start the development server"
    kill $DEV_PID 2>/dev/null
    exit 1
fi

echo "✅ AI Chatbot Reference is running successfully!"
echo "🌐 Open your browser and navigate to: http://localhost:$PORT"
echo ""
echo "� Features available:"
echo "   - AI SDK 5 Beta with OpenAI integration"
echo "   - Advanced streaming responses"
echo "   - Modern UI with Tailwind CSS"
echo "   - Reference implementation for learning"
echo ""
echo "� Compare with our simple chat-ui in the chat-ui/ folder"
echo "📖 See ai-chatbot-reference/README-REFERENCE.md for details"
echo ""
echo "🛑 To stop the server, press Ctrl+C or run: pkill -f 'next dev'"

# Keep the script running to show logs
wait $DEV_PID
