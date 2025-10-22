// AWS SDK v3
import { S3Client } from '@aws-sdk/client-s3';
import { LambdaClient } from '@aws-sdk/client-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb';

const awsConfig = {
  region: process.env.AWS_REGION || process.env.NEXT_PUBLIC_AWS_REGION || 'us-east-1',
  credentials: process.env.AWS_ACCESS_KEY_ID ? {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  } : undefined,
};

export const getS3Client = () => {
  return new S3Client(awsConfig);
};

export const getDynamoDBClient = () => {
  const client = new DynamoDBClient(awsConfig);
  return DynamoDBDocumentClient.from(client);
};

export const getLambdaClient = () => {
  return new LambdaClient(awsConfig);
};
