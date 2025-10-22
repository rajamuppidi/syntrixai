import { NextRequest, NextResponse } from 'next/server';
import { PutObjectCommand } from '@aws-sdk/client-s3';
import { InvokeCommand } from '@aws-sdk/client-lambda';
import { getS3Client, getLambdaClient } from '@/app/lib/aws';

const BUCKET_NAME = process.env.NEXT_PUBLIC_S3_CLINICAL_NOTES_BUCKET!;

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      );
    }

    // Read file content
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Upload to S3
    const s3 = getS3Client();
    const s3Key = `notes/${Date.now()}_${file.name}`;
    await s3.send(new PutObjectCommand({
      Bucket: BUCKET_NAME,
      Key: s3Key,
      Body: buffer,
      ContentType: file.type || 'text/plain',
    }));

    console.log(`✅ Uploaded to S3: ${s3Key}`);

    // Invoke extraction Lambda
    const lambda = getLambdaClient();
    const extractionResult = await lambda.send(new InvokeCommand({
      FunctionName: 'pa-extraction-agent',
      InvocationType: 'RequestResponse',
      Payload: Buffer.from(JSON.stringify({
        bucket: BUCKET_NAME,
        key: s3Key,
      })),
    }));

    const extractionResponse = JSON.parse(new TextDecoder().decode(extractionResult.Payload));
    const extractionBody = typeof extractionResponse.body === 'string'
      ? JSON.parse(extractionResponse.body)
      : extractionResponse.body;

    console.log('✅ Extraction complete:', extractionBody);

    // Check for FHIR parser error
    if (extractionBody.error && extractionBody.error.includes('FHIR parser not available')) {
      return NextResponse.json(
        {
          error: 'FHIR parser module not deployed to Lambda. The FHIR parser needs to be included in the Lambda deployment package. For now, please use plain text (.txt) files.',
          message: 'FHIR parser not configured in Lambda deployment',
          case_id: null,
        },
        { status: 400 }
      );
    }

    // Check for other errors
    if (extractionBody.error) {
      return NextResponse.json(
        {
          error: extractionBody.error,
          message: extractionBody.message || 'Extraction failed',
        },
        { status: 500 }
      );
    }

    return NextResponse.json(extractionBody);
  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Upload failed' },
      { status: 500 }
    );
  }
}
