import boto3
import base64
import uuid
import os
import PyPDF2
from flask import Flask, Blueprint, request, jsonify
from boto3.dynamodb.conditions import Key
from Utils.UtilFunctions import fetchChatGPTResponseByJobId, createCandidateFitAnalysisQuery, extractTextFromPDF
import json

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
job_table = dynamodb.Table('job')
s3_client = boto3.client('s3')
s3_bucket = 'cv-transient-data'
sqsClient = boto3.client('sqs')
sqsQueueName = 'ChatGPTProcessQueue'

candidate_fit = Blueprint('candidateFit', __name__)

@candidate_fit.route("/analysis", methods=['POST'])
def register():
    candidateCV = extractTextFromPDF(request.files['candidateCV'])
    job_description = request.files["jobDescription"].read()

    job_id = str(uuid.uuid4())
    job = job_table.put_item(Item={'id':job_id, 'status': 'InProgress'})
    s3_file_name = f"{job_id}_candidateCV.txt"

    chatGPTQuery = createCandidateFitAnalysisQuery(str(candidateCV), str(job_description))

    with open('chatGPTQueryFile.txt', 'w', encoding='utf-8') as chatGPTQueryFile:
        chatGPTQueryFile.write(chatGPTQuery)

    # Save the file to S3
    s3_key = f"ChatGPTQueries/{s3_file_name}"
    s3_client.upload_file('chatGPTQueryFile.txt', s3_bucket, s3_key)

    # Remove the temporary local file
    os.remove('chatGPTQueryFile.txt')

    SQSMessage = {
        'jobId': job_id,
        'chatGPTQueryS3Path': f's3://{s3_bucket}/{s3_key}'
    }

    sqsQueryURL =sqsClient.get_queue_url(QueueName=sqsQueueName)
    print(sqsQueryURL['QueueUrl'])
    print(type(sqsQueryURL))

    response = sqsClient.send_message(QueueUrl=sqsQueryURL['QueueUrl'], MessageBody=json.dumps(SQSMessage))

    return jsonify(message="Job created:" + job_id + " SQS:" + str(response)), 200

@candidate_fit.route("/report")
def getReport():
    jobId = request.args.get('jobId')
    if jobId:
        return fetchChatGPTResponseByJobId(jobId)
    else:
        return jsonify({'error': 'Job ID is missing in the query parameters'}), 400

