import boto3
import base64
import uuid
import os
import PyPDF2
from flask import Flask, Blueprint, request, jsonify
from boto3.dynamodb.conditions import Key
import json

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')  # DynamoDB resource
jobTable = dynamodb.Table('job')  # DynamoDB table
s3Client = boto3.client('s3')  # S3 client
s3Bucket = 'cv-transient-data'  # S3 bucket name
sqsClient = boto3.client('sqs')  # SQS client
sqsQueueName = 'ChatGPTProcessQueue'  # SQS queue name

def fetchChatGPTResponseByJobId(jobId):
    try:
        # Retrieve resultS3Path from DynamoDB
        response = jobTable.get_item(
            Key={'id': jobId},
            ProjectionExpression='resultS3Path'
        )
        item = response.get('Item', {})
        resultS3Path = item.get('resultS3Path', '')

        if not resultS3Path:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Result not found for the given jobId'})
            }

        # Extract S3 key
        s3Key = resultS3Path.split(f'{s3Bucket}/')[1]

        localFilePath = 'chatGPTResFile.txt'

        # Download file from S3
        s3Client.download_file(s3Bucket, s3Key, localFilePath)

        # Read the contents of the file
        with open(localFilePath, 'r', encoding='utf-8') as chatGPTResFile:
            result = chatGPTResFile.read()

        return {
            'statusCode': 200,
            'body': json.dumps({'Result': result})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error retrieving result from S3: {e}'})
        }
    finally:
        # Remove the temporary local file
        os.remove(localFilePath)


def createCandidateFitAnalysisQuery(candidateCV, jobDescription):
    # Strings for formatting the query
    startCandidateCV = "\nSTART CANDIDATE CV\n"
    endCandidateCV = "\nEND CANDIDATE CV\n"
    startJobDescription = "\nSTART JOB DESCRIPTION\n"
    endJobDescription = "\nEND JOB DESCRIPTION\n"

    # Question for fit analysis
    fitAnalysisQuestion = "Is this candidate fit for the job description mentioned above? Give detailed analysis"
    
    # Construct the query
    return startCandidateCV + str(candidateCV) + endCandidateCV + startJobDescription + str(jobDescription) + endJobDescription + fitAnalysisQuestion

def createCandidateCompareAnalysisQuery(candidateCV1, candidateCV2, jobDescription):
    # Strings for formatting the query
    startCandidateCV = "\nSTART {candidate} CANDIDATE CV\n"
    endCandidateCV = "\nEND {candidate} CANDIDATE CV\n"
    startJobDescription = "\nSTART JOB DESCRIPTION\n"
    endJobDescription = "\nEND JOB DESCRIPTION\n"

    # Question for compare analysis
    candidateCompareAnalysisQuestion = "Compare candidates against the provided job description? Give detailed analysis"

    # Construct the query for both candidates
    candidate1 = startCandidateCV.format(candidate="1st") + str(candidateCV1) + endCandidateCV.format(candidate="1st")
    candidate2 = startCandidateCV.format(candidate="2nd") + str(candidateCV2) + endCandidateCV.format(candidate="2nd")

    # Combine the queries
    return candidate1 + candidate2 + startJobDescription + str(jobDescription) + endJobDescription + candidateCompareAnalysisQuestion


def getChatGPTResponse(query):
    return query


def extractTextFromPDF(pdfFile):
    # Extract text from a PDF file
    pdfReader = PyPDF2.PdfReader(pdfFile)
    text = ''
    for pageNumber in range(len(pdfReader.pages)):
        page = pdfReader.pages[pageNumber]
        text += page.extract_text()
    return text
