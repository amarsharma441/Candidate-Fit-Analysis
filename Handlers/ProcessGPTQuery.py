import boto3
import base64
import uuid
import os
import PyPDF2
from flask import Flask, Blueprint, request, jsonify
from boto3.dynamodb.conditions import Key
from Utils.UtilFunctions import getChatGPTResponse
import json

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
job_table = dynamodb.Table('job')
s3_client = boto3.client('s3')
s3_bucket = 'cv-transient-data'
sqsClient = boto3.client('sqs')
sqsQueueName = 'ChatGPTProcessQueue'

def processQuery(event, context):
    message_body = json.loads(event['Records'][0]['body'])
    print(message_body)
    print(type(message_body))

    try:
        s3_key = message_body['chatGPTQueryS3Path'].split(f'{s3_bucket}/')[1]
        local_file_path = '/tmp/chatGPTQueryFile.txt'
        s3_client.download_file(s3_bucket, s3_key, local_file_path)


        with open(local_file_path, 'r', encoding='utf-8') as chatGPTQueryFile:
            chatGPTQuery = chatGPTQueryFile.read()

        print(chatGPTQuery)
        chatGPTResponse = getChatGPTResponse(chatGPTQuery)

        with open('/tmp/chatGPTResponseFile.txt', 'w', encoding='utf-8') as chatGPTResponseFile:
            chatGPTResponseFile.write(chatGPTResponse)

        # Save the file to S3
        job_id = message_body['jobId']
        s3_file_name = f"{job_id}_chatGPTResponse.txt"
        s3_key = f"ChatGPTResponses/{s3_file_name}"
        s3_client.upload_file('/tmp/chatGPTResponseFile.txt', s3_bucket, s3_key)
        s3_result_path = f's3://{s3_bucket}/{s3_key}'
        # Remove the temporary local files
        print(s3_result_path)
        os.remove(local_file_path)
        os.remove('/tmp/chatGPTResponseFile.txt')

        job_table.update_item(
            Key={'id': message_body['jobId']},
            UpdateExpression='SET resultS3Path = :path, #status = :status',
            ExpressionAttributeValues={':path': s3_result_path, ':status': 'completed'},
            ExpressionAttributeNames={'#status': 'status'}
        )
    except Exception as e:
        print(f"Todo: Handle the error or move the message to a dead-letter queue: {e}")
    finally:
        sqsQueryURL =sqsClient.get_queue_url(QueueName=sqsQueueName)
        sqsClient.delete_message(
            QueueUrl=sqsQueryURL['QueueUrl'],
            ReceiptHandle=event['Records'][0]['receiptHandle']
        )


    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Processing completed'})
    }
