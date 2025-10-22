import { NextResponse } from 'next/server';
import { ScanCommand } from '@aws-sdk/lib-dynamodb';
import { getDynamoDBClient } from '@/app/lib/aws';

const TABLE_NAME = process.env.NEXT_PUBLIC_DYNAMODB_TABLE || 'pa-agent-cases';

export async function GET() {
  try {
    const dynamodb = getDynamoDBClient();
    const result = await dynamodb.send(new ScanCommand({
      TableName: TABLE_NAME,
    }));

    // Sort by created_at descending
    const cases = (result.Items || []).sort((a, b) => {
      const dateA = new Date(a.created_at || 0).getTime();
      const dateB = new Date(b.created_at || 0).getTime();
      return dateB - dateA;
    });

    return NextResponse.json(cases);
  } catch (error) {
    console.error('Failed to fetch cases:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch cases' },
      { status: 500 }
    );
  }
}
