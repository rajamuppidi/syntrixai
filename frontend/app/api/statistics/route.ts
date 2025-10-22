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

    const cases = result.Items || [];

    const stats = {
      total_cases: cases.length,
      approved: cases.filter((c) => c.status === 'approved').length,
      denied: cases.filter((c) => c.status === 'denied').length,
      pending: cases.filter((c) =>
        ['pending', 'extracted', 'processing'].includes(c.status)
      ).length,
    };

    const completed = stats.approved + stats.denied;
    const approvalRate = completed > 0
      ? Math.round((stats.approved / completed) * 100 * 10) / 10
      : 0;

    const completionRate = stats.total_cases > 0
      ? Math.round((completed / stats.total_cases) * 100 * 10) / 10
      : 0;

    // Top denial reasons
    const denialReasons: Record<string, number> = {};
    cases
      .filter((c) => c.status === 'denied')
      .forEach((c) => {
        const reason = c.payer_response?.reason || 'Unknown';
        denialReasons[reason] = (denialReasons[reason] || 0) + 1;
      });

    const topDenialReasons = Object.entries(denialReasons)
      .map(([reason, count]) => ({ reason, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    return NextResponse.json({
      total_cases: stats.total_cases,
      approved: stats.approved,
      denied: stats.denied,
      pending: stats.pending,
      approval_rate: approvalRate,
      completion_rate: completionRate,
      top_denial_reasons: topDenialReasons,
    });
  } catch (error) {
    console.error('Failed to fetch statistics:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch statistics' },
      { status: 500 }
    );
  }
}
