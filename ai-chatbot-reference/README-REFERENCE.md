# Vercel AI Chatbot Reference

This folder contains the official [Vercel AI Chatbot](https://github.com/vercel/ai-chatbot) as a reference implementation for AI SDK 5 Beta.

## Purpose

This reference implementation serves as:

1. **Learning Resource**: See best practices for AI SDK 5 implementation
2. **Feature Comparison**: Compare our Temporal-focused chat-ui with a full-featured chatbot
3. **Migration Guide**: Understand advanced AI SDK 5 patterns and features
4. **Inspiration**: Discover new capabilities for future enhancements

## Key Features in Reference Implementation

### 🤖 **AI SDK 5 Beta Features**
- **Version**: `ai@5.0.0-beta.6`
- **Multi-provider support**: OpenAI, Anthropic, Google, etc.
- **Advanced streaming**: Real-time UI updates
- **Tool calling**: Web search, code execution, document processing
- **Multi-modal**: Text, images, and file uploads

### 🎨 **UI/UX Features**
- **Modern interface**: Beautiful, responsive design with Tailwind CSS
- **Real-time streaming**: Character-by-character response streaming
- **File uploads**: Image and document support
- **Chat history**: Persistent conversation management
- **User authentication**: Complete user management system

### 🛠 **Technical Features**
- **Database integration**: PostgreSQL with Drizzle ORM
- **Authentication**: NextAuth.js 5.0 beta
- **Testing**: Playwright end-to-end tests
- **Monitoring**: OpenTelemetry integration
- **Deployment**: Vercel-optimized

## Key Differences from Our Implementation

| Feature | Our chat-ui | Vercel Reference |
|---------|-------------|------------------|
| **Focus** | Temporal workflow assistance | General-purpose chatbot |
| **AI SDK Version** | 5.0 Beta | 5.0 Beta (same) |
| **Database** | None (stateless) | PostgreSQL with full persistence |
| **Authentication** | None | Full user management |
| **File Support** | None | Images, documents, CSV |
| **Tools** | None | Web search, code execution |
| **UI Framework** | Custom Tailwind | Radix UI + Tailwind |
| **Complexity** | Simple, focused | Full-featured application |

## Staying in Sync

To update the reference implementation:

```bash
# Easy sync with our custom alias
git sync-chatbot

# Or the full command
git subtree pull --prefix=ai-chatbot-reference https://github.com/vercel/ai-chatbot.git main --squash
```

## Learning Opportunities

### 1. **Advanced AI SDK 5 Patterns**
- Look at `ai-chatbot-reference/app/api/chat/route.ts` for advanced streaming
- Check `ai-chatbot-reference/lib/ai/` for multi-provider setup
- Study tool implementations in `ai-chatbot-reference/lib/tools/`

### 2. **UI Components**
- Examine `ai-chatbot-reference/components/chat/` for chat UI patterns
- Study `ai-chatbot-reference/components/ui/` for reusable components
- Check streaming patterns in React components

### 3. **Database Integration**
- See `ai-chatbot-reference/lib/db/` for conversation persistence
- Study user management patterns
- Learn about chat history implementation

### 4. **Testing Patterns**
- Check `ai-chatbot-reference/tests/` for E2E testing with Playwright
- Study API testing patterns
- Learn about chat flow testing

## Potential Enhancements for Our Chat-UI

Based on the reference implementation, we could consider:

1. **Tool Integration**: Add Temporal-specific tools
   - Workflow status checking
   - Activity execution monitoring
   - Error diagnosis assistance

2. **Enhanced Streaming**: Improve real-time feedback
   - Progress indicators for long operations
   - Structured response formatting
   - Better error handling

3. **Conversation Context**: Add conversation memory
   - Remember previous workflow discussions
   - Context-aware suggestions
   - Session persistence

4. **Multi-modal Support**: Support for diagrams and files
   - Workflow diagram uploads
   - Configuration file analysis
   - Log file processing

## Running the Reference Implementation

**⚠️ Database Requirement**: The reference implementation requires a PostgreSQL database for authentication and chat persistence. For local testing, you have a few options:

### Option 1: Quick Testing (Limited Functionality)
```bash
cd ai-chatbot-reference
pnpm dev
# Visit http://localhost:3001
# Note: Authentication will fail, but you can explore the UI
```

### Option 2: Full Setup with Database
```bash
cd ai-chatbot-reference

# 1. Set up a local PostgreSQL database or use Vercel Postgres
# 2. Copy and configure environment variables
cp .env.example .env
# Edit .env with your database credentials

# 3. Run database migrations
pnpm db:migrate

# 4. Start the development server
pnpm dev
```

### Option 3: Use Our Simplified Chat-UI Instead
For immediate AI chat functionality without database setup:
```bash
# Go back to our simplified implementation
cd ../chat-ui
npm run dev
# Visit http://localhost:3000 - works immediately!
```

### Environment Variables Needed for Full Functionality

```bash
# Required for authentication
AUTH_SECRET=your-generated-secret

# Required for AI functionality  
XAI_API_KEY=your-openai-api-key

# Required for full functionality
POSTGRES_URL=your-postgres-connection-string
BLOB_READ_WRITE_TOKEN=your-vercel-blob-token
REDIS_URL=your-redis-connection-string
```

## Security Note

The reference implementation includes advanced security patterns:
- Environment variable management
- API key protection
- User authentication
- Input validation

These patterns complement our pre-commit hook security system.
