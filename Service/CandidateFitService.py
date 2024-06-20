import boto3
import base64
import uuid
import os
import PyPDF2
from boto3.dynamodb.conditions import Key
from Utils.UtilFunctions import fetchChatGPTResponseByJobId, createCandidateFitAnalysisQuery, extractTextFromPDF, createCandidateCompareAnalysisQuery
import json

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
jobTable = dynamodb.Table('job')

# Initialize S3 client
s3Client = boto3.client('s3')
s3Bucket = 'cv-transient-data'

# Initialize SQS client
sqsClient = boto3.client('sqs')
sqsQueueName = 'ChatGPTProcessQueue'

def candidateFitAnalysis(reqForCandidateCompare, candidateCV1, candidateCV2, jobDescription):
    reqForCandidateCompare = reqForCandidateCompare.lower() == 'True'.lower()

    # Extract text from candidate CV(s)
    candidateCV1 = extractTextFromPDF(candidateCV1)
    if reqForCandidateCompare:
        candidateCV2 = extractTextFromPDF(candidateCV2)

    # Generate a unique job ID
    jobId = str(uuid.uuid4())

    # Insert job details into DynamoDB
    jobTable.put_item(Item={'id': jobId, 'status': 'InProgress'})

    # Generate S3 file name
    s3FileName = f"{jobId}_Query.txt"

    # Create a ChatGPT query
    if reqForCandidateCompare:
        chatGPTQuery = createCandidateCompareAnalysisQuery(str(candidateCV1), str(candidateCV2), str(jobDescription))
    else:
        chatGPTQuery = createCandidateFitAnalysisQuery(str(candidateCV1), str(jobDescription))
        
    # Save the ChatGPT query to a local file
    with open('/tmp/chatGPTQueryFile.txt', 'w', encoding='utf-8') as chatGPTQueryFile:
        chatGPTQueryFile.write(chatGPTQuery)

    # Save the file to S3
    s3Key = f"ChatGPTQueries/{s3FileName}"
    s3Client.upload_file('/tmp/chatGPTQueryFile.txt', s3Bucket, s3Key)

    # Remove the temporary local file
    os.remove('/tmp/chatGPTQueryFile.txt')

    # SQS message containing job details
    sqsMessage = {
        'jobId': jobId,
        'chatGPTQueryS3Path': f's3://{s3Bucket}/{s3Key}'
    }

    # Get the SQS queue URL
    sqsQueueUrl = sqsClient.get_queue_url(QueueName=sqsQueueName)['QueueUrl']

    # Send the SQS message
    response = sqsClient.send_message(QueueUrl=sqsQueueUrl, MessageBody=json.dumps(sqsMessage))

    return {"message": "Job created:" + jobId + " SQS:" + str(response)}

def getReport(jobId):
    if jobId:
        return fetchChatGPTResponseByJobId(jobId)
    else:
        return {'error': 'Job ID is missing in the query parameters'}

def resourceNotFound(e):
    return {'error': 'Not found!'}