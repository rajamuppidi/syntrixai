import { NextRequest, NextResponse } from 'next/server';
import { GetCommand } from '@aws-sdk/lib-dynamodb';
import { getDynamoDBClient } from '@/app/lib/aws';

const TABLE_NAME = process.env.NEXT_PUBLIC_DYNAMODB_TABLE || 'pa-agent-cases';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const dynamodb = getDynamoDBClient();
    const result = await dynamodb.send(new GetCommand({
      TableName: TABLE_NAME,
      Key: { case_id: id },
    }));

    if (!result.Item) {
      return NextResponse.json(
        { error: 'Case not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(result.Item);
  } catch (error) {
    console.error('Failed to fetch case:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch case' },
      { status: 500 }
    );
  }
}
