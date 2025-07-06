# Temporal Flow Chat UI

A React-based chat interface for interacting with your Temporal workflow engine using LlamaIndex Chat UI components.

## Features

- Modern chat interface built with Next.js and React
- Integration with LlamaIndex Chat UI components
- Responsive design with Tailwind CSS
- Streaming chat responses
- Docker containerization

## Quick Start

### Run with Docker Compose

1. Build and start the chat UI service:
   ```bash
   docker-compose --profile ui up -d chat-ui
   ```

2. Access the chat interface at: http://localhost:3000

### Run the complete stack

To run the chat UI along with your Temporal services:

```bash
# Start core Temporal services
docker-compose up -d temporal temporal-ui postgresql

# Start your workflow workers
docker-compose up -d incident-worker root-orchestrator-worker

# Start the chat UI
docker-compose --profile ui up -d chat-ui
```

### Access Points

- **Chat UI**: http://localhost:3000
- **Temporal UI**: http://localhost:8080
- **Temporal Server**: localhost:7233

## Development

### Local Development Setup

1. Navigate to the chat-ui directory:
   ```bash
   cd chat-ui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open http://localhost:3000 in your browser

### Project Structure

```
chat-ui/
├── app/
│   ├── api/chat/route.ts      # Chat API endpoint
│   ├── globals.css            # Global styles with theme
│   ├── layout.tsx             # Root layout
│   └── page.tsx               # Main chat component
├── package.json               # Dependencies
├── next.config.js             # Next.js configuration
├── tailwind.config.js         # Tailwind CSS configuration
└── tsconfig.json              # TypeScript configuration
```

## Customization

### Modifying the Chat API

Edit `chat-ui/app/api/chat/route.ts` to integrate with your Temporal workflows:

```typescript
// Example: Query workflow status
const workflowHandle = await client.workflow.getHandle(workflowId);
const result = await workflowHandle.query('getStatus');
```

### Styling

The application uses Tailwind CSS with a custom theme defined in `globals.css`. You can modify colors and styling by updating the CSS custom properties.

### Adding Features

The chat interface is built with composable components. You can extend it by:

- Adding custom input components
- Implementing file upload functionality
- Adding workflow-specific commands
- Integrating with external APIs

## Docker Configuration

The chat UI is containerized using a multi-stage Docker build:

- **Dependencies stage**: Installs npm packages
- **Builder stage**: Builds the Next.js application
- **Runner stage**: Creates production image

The build is optimized for production with:
- Standalone output for minimal image size
- Proper user permissions
- Health checks
- Environment variable support

## Troubleshooting

### Common Issues

1. **Chat UI not loading**: Check that port 3000 is available and the container is running
2. **Styles not applied**: Ensure Tailwind CSS is properly configured and CSS files are imported
3. **API errors**: Verify the chat API route is accessible and returning proper responses

### Logs

View chat UI logs:
```bash
docker-compose logs chat-ui
```

### Rebuilding

If you make changes to the chat UI code:
```bash
docker-compose --profile ui down chat-ui
docker-compose --profile ui up -d --build chat-ui
```

## Integration with Temporal

The chat interface is designed to work with your existing Temporal workflow engine. You can extend the API to:

- Start new workflow executions
- Query workflow status
- Send signals to running workflows
- Retrieve workflow history
- Monitor activity execution

See the API route in `chat-ui/app/api/chat/route.ts` for examples of how to integrate with your Temporal client.
