import boto3
import base64
import uuid
import os
import PyPDF2
from flask import Flask, Blueprint, request, jsonify, make_response
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

# Blueprint for candidate fit analysis
candidateFit = Blueprint('candidateFit', __name__)

@candidateFit.route("/analysis", methods=['POST'])
def candidateFitAnalysis():
    # Get reqForCandidateCompare from query parameters
    reqForCandidateCompare = request.args.get('reqForCandidateCompare')
    if not reqForCandidateCompare:
        # Return an error if reqForCandidateCompare is missing in the query parameters
        return jsonify({'error': 'reqForCandidateCompare is missing in the query parameters'}), 400
    reqForCandidateCompare = reqForCandidateCompare.lower() == 'True'.lower()

    # Extract text from candidate CV(s)
    candidateCV1 = extractTextFromPDF(request.files['candidateCV1'])
    if reqForCandidateCompare == True:
        candidateCV2 = extractTextFromPDF(request.files['candidateCV2'])

    # Read job description file
    jobDescription = request.files["jobDescription"].read()

    # Generate a unique job ID
    jobId = str(uuid.uuid4())

    # Insert job details into DynamoDB
    jobTable.put_item(Item={'id': jobId, 'status': 'InProgress'})

    # Generate S3 file name
    s3FileName = f"{jobId}_Query.txt"

    # Create a ChatGPT query
    if reqForCandidateCompare == True:
        chatGPTQuery = createCandidateCompareAnalysisQuery(str(candidateCV1), str(candidateCV2) , str(jobDescription))
    else:
        chatGPTQuery = createCandidateFitAnalysisQuery(str(candidateCV1), str(jobDescription))
        
    # Save the ChatGPT query to a local file
    with open('chatGPTQueryFile.txt', 'w', encoding='utf-8') as chatGPTQueryFile:
        chatGPTQueryFile.write(chatGPTQuery)

    # Save the file to S3
    s3Key = f"ChatGPTQueries/{s3FileName}"
    s3Client.upload_file('chatGPTQueryFile.txt', s3Bucket, s3Key)

    # Remove the temporary local file
    os.remove('chatGPTQueryFile.txt')

    # SQS message containing job details
    sqsMessage = {
        'jobId': jobId,
        'chatGPTQueryS3Path': f's3://{s3Bucket}/{s3Key}'
    }

    # Get the SQS queue URL
    sqsQueueUrl = sqsClient.get_queue_url(QueueName=sqsQueueName)['QueueUrl']

    # Send the SQS message
    response = sqsClient.send_message(QueueUrl=sqsQueueUrl, MessageBody=json.dumps(sqsMessage))

    return jsonify(message="Job created:" + jobId + " SQS:" + str(response)), 200


@candidateFit.route("/report")
def getReport():
    # Get jobId from query parameters
    jobId = request.args.get('jobId')

    if jobId:
        # Fetch and return ChatGPT response for the given jobId
        return fetchChatGPTResponseByJobId(jobId)
    else:
        # Return an error if jobId is missing in the query parameters
        return jsonify({'error': 'Job ID is missing in the query parameters'}), 400


@candidateFit.errorhandler(404)
def resourceNotFound(e):
    # Custom error handler for 404 Not Found
    return make_response(jsonify(error='Not found!'), 404)