import { streamText, convertToCoreMessages, UIMessage } from 'ai'
import { openai } from '@ai-sdk/openai'

export async function POST(request: Request) {
  try {
    const { messages }: { messages: UIMessage[] } = await request.json()

    const result = await streamText({
      model: openai('gpt-4o-mini'),
      messages: convertToCoreMessages([
        {
          role: 'system',
          content: `You are a helpful AI assistant specializing in Temporal workflow orchestration. You have deep knowledge of:

• Temporal workflows and activities
• Error handling and retry policies  
• Workflow state management
• Task queues and workers
• Signals and queries
• Temporal best practices
• Python and TypeScript Temporal SDKs

You help users design, implement, and troubleshoot Temporal-based applications. Always provide practical, actionable advice with code examples when relevant.`
        },
        ...messages
      ]),
    })

    return result.toDataStreamResponse()
  } catch (error) {
    console.error('Chat API error:', error)
    return Response.json(
      { error: 'Failed to process chat request' },
      { status: 500 }
    )
  }
}
