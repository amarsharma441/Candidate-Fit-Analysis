import boto3
import base64
import uuid
import os
import PyPDF2
from boto3.dynamodb.conditions import Key
from Utils.UtilFunctions import fetchChatGPTResponseByJobId, createCandidateFitAnalysisQuery, extractTextFromPDF, createCandidateCompareAnalysisQuery
import json

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
jobTable = dynamodb.Table('job')

s3Client = boto3.client('s3')
s3Bucket = 'cv-transient-data'

sqsClient = boto3.client('sqs')
sqsQueueName = 'ChatGPTProcessQueue'

def candidateFitAnalysis(reqForCandidateCompare, candidateCV1, candidateCV2, jobDescription):
    """
    Analyzes the fit of a candidate or compares two candidates for a given job description.

    Args:
        reqForCandidateCompare (str): Indicates if the comparison between two candidates is required.
        candidateCV1 (bytes): PDF file content of the first candidate's CV.
        candidateCV2 (bytes): PDF file content of the second candidate's CV (optional).
        jobDescription (str): Description of the job for which the analysis is being performed.

    Returns:
        dict: A message indicating the job ID and SQS response.
    """
    # Convert the comparison request to boolean
    reqForCandidateCompare = reqForCandidateCompare.lower() == 'true'

    # Extract text from candidate CVs
    candidateCV1 = extractTextFromPDF(candidateCV1)
    candidateCV2 = extractTextFromPDF(candidateCV2) if reqForCandidateCompare else None

    # Generate a unique job ID
    jobId = str(uuid.uuid4())

    # Insert job details into DynamoDB
    jobTable.put_item(Item={'id': jobId, 'status': 'InProgress'})

    # Generate S3 file name
    s3FileName = f"{jobId}_Query.txt"

    # Create a ChatGPT query based on the type of analysis
    if reqForCandidateCompare:
        chatGPTQuery = createCandidateCompareAnalysisQuery(str(candidateCV1), str(candidateCV2), str(jobDescription))
    else:
        chatGPTQuery = createCandidateFitAnalysisQuery(str(candidateCV1), str(jobDescription))

    # Save the ChatGPT query to a temporary local file
    tmpFilePath = '/tmp/chatGPTQueryFile.txt'
    with open(tmpFilePath, 'w', encoding='utf-8') as chatGPTQueryFile:
        chatGPTQueryFile.write(chatGPTQuery)

    # Upload the file to S3
    s3Key = f"ChatGPTQueries/{s3FileName}"
    s3Client.upload_file(tmpFilePath, s3Bucket, s3Key)

    # Remove the temporary local file
    os.remove(tmpFilePath)

    # Prepare SQS message containing job details
    sqsMessage = {
        'jobId': jobId,
        'chatGPTQueryS3Path': f's3://{s3Bucket}/{s3Key}'
    }

    # Get the SQS queue URL and send the SQS message
    sqsQueueUrl = sqsClient.get_queue_url(QueueName=sqsQueueName)['QueueUrl']
    response = sqsClient.send_message(QueueUrl=sqsQueueUrl, MessageBody=json.dumps(sqsMessage))

    return {"message": f"Job created: {jobId} SQS: {str(response)}"}

def getReport(jobId):
    """
    Fetches the analysis report for a given job ID.

    Args:
        jobId (str): The ID of the job for which the report is being fetched.

    Returns:
        dict: The analysis report or an error message if the job ID is missing.
    """
    if jobId:
        return fetchChatGPTResponseByJobId(jobId)
    else:
        return {'error': 'Job ID is missing in the query parameters'}

def resourceNotFound(e):
    """
    Handles resource not found errors.

    Args:
        e (Exception): The exception that was raised.

    Returns:
        dict: An error message indicating the resource was not found.
    """
    return {'error': 'Not found!'}