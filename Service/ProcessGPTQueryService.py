import boto3
import os
import json
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from Utils.UtilFunctions import getChatGPTResponse

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
jobTable = dynamodb.Table('job')

s3Client = boto3.client('s3')
s3Bucket = 'cv-transient-data'

sqsClient = boto3.client('sqs')
sqsQueueName = 'ChatGPTProcessQueue'

def processQuery(event, context):
    """
    Processes an SQS event to handle ChatGPT query execution and result storage.

    Args:
        event (dict): The SQS event containing the message body.
        context: AWS Lambda context object (not used in this function).

    Returns:
        dict: A response dictionary with a status code and message.
    """
    # Extract message body from the SQS event
    messageBody = json.loads(event['Records'][0]['body'])

    try:
        # Extract S3 key from the message and download the ChatGPT query file
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

        # Save the response file to S3
        jobId = messageBody['jobId']
        s3FileName = f"{jobId}_chatGPTResponse.txt"
        s3Key = f"ChatGPTResponses/{s3FileName}"
        s3Client.upload_file(localResponseFilePath, s3Bucket, s3Key)
        s3ResultPath = f's3://{s3Bucket}/{s3Key}'

        # Remove the temporary local files
        os.remove(localFilePath)
        os.remove(localResponseFilePath)

        # Set the expiration time for the result (1 day)
        expirationTime = datetime.utcnow() + timedelta(days=1)
        expirationTimestamp = int(expirationTime.timestamp())

        # Update job status and result S3 path in DynamoDB
        jobTable.update_item(
            Key={'id': jobId},
            UpdateExpression='SET resultS3Path = :path, #status = :status, #timeToLive = :timeToLive',
            ExpressionAttributeValues={
                ':path': s3ResultPath,
                ':status': 'completed',
                ':timeToLive': expirationTimestamp
            },
            ExpressionAttributeNames={
                '#status': 'status',
                '#timeToLive': 'timeToLive'
            }
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
