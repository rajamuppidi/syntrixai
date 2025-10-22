import { NextRequest, NextResponse } from 'next/server';
import { InvokeCommand } from '@aws-sdk/client-lambda';
import { getLambdaClient } from '@/app/lib/aws';

export async function POST(request: NextRequest) {
  try {
    const { case_id } = await request.json();

    if (!case_id) {
      return NextResponse.json(
        { error: 'case_id is required' },
        { status: 400 }
      );
    }

    console.log(`🔄 Starting orchestration for case: ${case_id}`);

    // Invoke orchestrator Lambda
    const lambda = getLambdaClient();
    const result = await lambda.send(new InvokeCommand({
      FunctionName: 'pa-orchestrator',
      InvocationType: 'RequestResponse',
      Payload: Buffer.from(JSON.stringify({ case_id })),
    }));

    const response = JSON.parse(new TextDecoder().decode(result.Payload));
    const body = typeof response.body === 'string'
      ? JSON.parse(response.body)
      : response.body;

    console.log('✅ Orchestration complete');

    return NextResponse.json({
      success: true,
      message: 'Orchestration completed',
      ...body,
    });
  } catch (error) {
    console.error('Orchestration error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Orchestration failed' },
      { status: 500 }
    );
  }
}
