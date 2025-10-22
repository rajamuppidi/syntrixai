import { NextRequest, NextResponse } from 'next/server';
import { BedrockRuntimeClient, ConverseCommand } from '@aws-sdk/client-bedrock-runtime';
import { ScanCommand, GetCommand } from '@aws-sdk/lib-dynamodb';
import { getDynamoDBClient } from '@/app/lib/aws';

const bedrock = new BedrockRuntimeClient({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: process.env.AWS_ACCESS_KEY_ID ? {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  } : undefined,
});

const TABLE_NAME = process.env.NEXT_PUBLIC_DYNAMODB_TABLE || 'pa-agent-cases';
const MODEL_ID = process.env.NEXT_PUBLIC_BEDROCK_MODEL_ID || 'amazon.nova-pro-v1:0';

// Tool definitions (same as in ai_assistant.py)
const TOOLS = [
  {
    toolSpec: {
      name: 'query_cases',
      description: 'Query prior authorization cases from the database based on filters like status, patient name, or diagnosis.',
      inputSchema: {
        json: {
          type: 'object',
          properties: {
            status: { type: 'string', description: 'Filter by status (approved, denied, pending)' },
            patient_name: { type: 'string', description: 'Filter by patient name' },
            diagnosis: { type: 'string', description: 'Filter by diagnosis' },
            limit: { type: 'integer', description: 'Max results to return (default 10)' },
          },
        },
      },
    },
  },
  {
    toolSpec: {
      name: 'get_case_details',
      description: 'Get complete details about a specific case by case ID or authorization number.',
      inputSchema: {
        json: {
          type: 'object',
          properties: {
            case_id: { type: 'string', description: 'Case ID (UUID) or authorization number (AUTH-*)' },
          },
          required: ['case_id'],
        },
      },
    },
  },
  {
    toolSpec: {
      name: 'get_statistics',
      description: 'Get overall statistics about all prior authorization cases.',
      inputSchema: {
        json: {
          type: 'object',
          properties: {},
        },
      },
    },
  },
];

// Tool implementations
async function queryCases(params: Record<string, unknown>) {
  const { status, patient_name, diagnosis, limit = 10 } = params;
  
  const dynamodb = getDynamoDBClient();
  const result = await dynamodb.send(new ScanCommand({ TableName: TABLE_NAME }));
  let cases = result.Items || [];

  if (status) {
    cases = cases.filter((c) => c.status?.toLowerCase() === String(status).toLowerCase());
  }
  if (patient_name) {
    cases = cases.filter((c) =>
      c.patient_name?.toLowerCase().includes(String(patient_name).toLowerCase())
    );
  }
  if (diagnosis) {
    cases = cases.filter((c) =>
      c.diagnosis?.toLowerCase().includes(String(diagnosis).toLowerCase())
    );
  }

  return { success: true, cases: cases.slice(0, Number(limit)) };
}

async function getCaseDetails(params: Record<string, unknown>) {
  const { case_id } = params;
  const dynamodb = getDynamoDBClient();

  // Try direct lookup
  try {
    const result = await dynamodb.send(new GetCommand({
      TableName: TABLE_NAME,
      Key: { case_id },
    }));

    if (result.Item) {
      return { success: true, case_data: result.Item };
    }
  } catch {}

  // Try authorization number lookup
  if (typeof case_id === 'string' && case_id.startsWith('AUTH-')) {
    const result = await dynamodb.send(new ScanCommand({
      TableName: TABLE_NAME,
      FilterExpression: 'authorization_number = :auth',
      ExpressionAttributeValues: { ':auth': case_id },
    }));

    if (result.Items && result.Items.length > 0) {
      return { success: true, case_data: result.Items[0] };
    }
  }

  return { success: false, message: 'Case not found' };
}

async function getStatistics() {
  const dynamodb = getDynamoDBClient();
  const result = await dynamodb.send(new ScanCommand({ TableName: TABLE_NAME }));
  const cases = result.Items || [];

  const stats = {
    total_cases: cases.length,
    approved: cases.filter((c) => c.status === 'approved').length,
    denied: cases.filter((c) => c.status === 'denied').length,
    pending: cases.filter((c) => ['pending', 'extracted', 'processing'].includes(c.status)).length,
    approval_rate: 0,
  };

  const completed = stats.approved + stats.denied;
  stats.approval_rate = completed > 0 ? Math.round((stats.approved / completed) * 100 * 10) / 10 : 0;

  return { success: true, statistics: stats };
}

export async function POST(request: NextRequest) {
  try {
    const { message, history = [] } = await request.json();

    // Build conversation history
    const messages = [
      ...history.map((msg: { role: string; content: string }) => ({
        role: msg.role,
        content: [{ text: msg.content }],
      })),
      {
        role: 'user',
        content: [{ text: message }],
      },
    ];

    let response = await bedrock.send(new ConverseCommand({
      modelId: MODEL_ID,
      messages,
      toolConfig: { 
        // @ts-expect-error - AWS SDK typing mismatch: toolSpec format is correct but doesn't match Tool[] type
        tools: TOOLS 
      },
      inferenceConfig: {
        temperature: 0.3,
        maxTokens: 2000,
      },
    }));

    // Handle tool calls
    while (response.stopReason === 'tool_use') {
      const toolUseBlock = response.output?.message?.content?.find((c: unknown) => {
        const content = c as { toolUse?: unknown };
        return content.toolUse !== undefined;
      });
      if (!toolUseBlock || !('toolUse' in toolUseBlock) || !toolUseBlock.toolUse) break;

      const toolUse = toolUseBlock.toolUse as { name: string; input: Record<string, unknown>; toolUseId: string };
      const toolName = toolUse.name;
      const toolInput = toolUse.input;
      const toolUseId = toolUse.toolUseId;

      let toolResult;
      if (toolName === 'query_cases') {
        toolResult = await queryCases(toolInput);
      } else if (toolName === 'get_case_details') {
        toolResult = await getCaseDetails(toolInput);
      } else if (toolName === 'get_statistics') {
        toolResult = await getStatistics();
      }

      messages.push({
        role: 'assistant',
        content: response.output?.message?.content || [],
      });

      messages.push({
        role: 'user',
        content: [
          {
            toolResult: {
              toolUseId,
              content: [{ json: toolResult }],
            },
          },
        ],
      });

      response = await bedrock.send(new ConverseCommand({
        modelId: MODEL_ID,
        messages,
        toolConfig: { 
          // @ts-expect-error - AWS SDK typing mismatch: toolSpec format is correct but doesn't match Tool[] type
          tools: TOOLS 
        },
        inferenceConfig: {
          temperature: 0.3,
          maxTokens: 2000,
        },
      }));
    }

    let aiResponse = response.output?.message?.content?.find((c: unknown) => {
      const content = c as { text?: string };
      return content.text !== undefined;
    })?.text as string || 'No response';

    // Remove <thinking> tags and their content
    aiResponse = aiResponse.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '').trim();

    return NextResponse.json({
      success: true,
      response: aiResponse,
    });
  } catch (error) {
    console.error('Chat error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Chat failed' },
      { status: 500 }
    );
  }
}
