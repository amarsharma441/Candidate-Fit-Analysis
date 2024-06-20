import boto3
import os
from boto3.dynamodb.conditions import Key
from Utils.UtilFunctions import getChatGPTResponse
import json
from datetime import datetime, timedelta

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
jobTable = dynamodb.Table('job')

# Initialize S3 client
s3Client = boto3.client('s3')
s3Bucket = 'cv-transient-data'

# Initialize SQS client
sqsClient = boto3.client('sqs')
sqsQueueName = 'ChatGPTProcessQueue'


def processQuery(event, context):
    # Extract message body from the SQS event
    messageBody = json.loads(event['Records'][0]['body'])

    try:
        # Extract S3 key and download the ChatGPT query file
        s3Key = messageBody['chatGPTQueryS3Path'].split(f'{s3Bucket}/')[1]
        localFilePath = '/tmp/chatGPTQueryFile.txt'
        s3Client.download_file(s3Bucket, s3Key, localFilePath)

        # Read ChatGPT query from the local file
        with open(localFilePath, 'r', encoding='utf-8') as chatGPTQueryFile:
            chatGPTQuery = chatGPTQueryFile.read()

        # Get ChatGPT response
        chatGPTResponse = getChatGPTResponse(chatGPTQuery)

        # Write ChatGPT response to a local file
        localResponseFilePath = '/tmp/chatGPTResponseFile.txt'
        with open(localResponseFilePath, 'w', encoding='utf-8') as chatGPTResponseFile:
            chatGPTResponseFile.write(chatGPTResponse)

        # Save the file to S3
        jobId = messageBody['jobId']
        s3FileName = f"{jobId}_chatGPTResponse.txt"
        s3Key = f"ChatGPTResponses/{s3FileName}"
        s3Client.upload_file(localResponseFilePath, s3Bucket, s3Key)
        s3ResultPath = f's3://{s3Bucket}/{s3Key}'

        # Remove the temporary local files
        os.remove(localFilePath)
        os.remove(localResponseFilePath)

        # Update job status and result S3 path in DynamoDB
        # Result will not be availeble for more than 1 day
        expirationTime = datetime.utcnow() + timedelta(days=1)
        expirationTimestamp = int(expirationTime.timestamp()) 
        jobTable.update_item(
            Key={'id': messageBody['jobId']},
            UpdateExpression='SET resultS3Path = :path, #status = :status, #timeToLive = :timeToLive',
            ExpressionAttributeValues={':path': s3ResultPath, ':status': 'completed', ':timeToLive': expirationTimestamp},
            ExpressionAttributeNames={'#status': 'status', '#timeToLive':'timeToLive'}
        )

    except Exception as e:
        # TODO: Handle the error or move the message to a dead-letter queue
        print(f"Todo: Handle the error or move the message to a dead-letter queue: {e}")
    finally:
        # Get SQS queue URL and delete the processed message
        sqsQueueUrl = sqsClient.get_queue_url(QueueName=sqsQueueName)['QueueUrl']
        sqsClient.delete_message(
            QueueUrl=sqsQueueUrl,
            ReceiptHandle=event['Records'][0]['receiptHandle']
        )

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Processing completed'})
    }
