import boto3
import base64
import uuid
import os
import PyPDF2
from flask import Flask, Blueprint, request, jsonify
from boto3.dynamodb.conditions import Key
import json

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
job_table = dynamodb.Table('job')
s3_client = boto3.client('s3')
s3_bucket = 'cv-transient-data'
sqsClient = boto3.client('sqs')
sqsQueueName = 'ChatGPTProcessQueue'

def fetchChatGPTResponseByJobId(jobId):
    print(jobId)
    response = job_table.get_item(
        Key={'id': jobId},
        ProjectionExpression='resultS3Path'
    )
    print(response)
    item = response.get('Item', {})
    resultS3Path = item.get('resultS3Path', '')

    if not resultS3Path:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Result not found for the given jobId'})
        }

    # Extract S3 key
    s3_key = resultS3Path.split(f'{s3_bucket}/')[1]

    local_file_path = 'chatGPTResFile.txt'
    
    try:
        # Download file from S3
        s3_client.download_file(s3_bucket, s3_key, local_file_path)

        # Read the contents of the file
        with open(local_file_path, 'r', encoding='utf-8') as chatGPTResFile:
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
        os.remove(local_file_path)


def createCandidateFitAnalysisQuery(candidateCV, jobDescription):
    startCandidateCV = "\nSTART CANDIDATE CV\n"
    endCandidateCV = "\nEND CANDIDATE CV\n"
    startJobDescription = "\nSTART JOB DESCRIPTION\n"
    endJobDescription = "\nEND JOB DESCRIPTION\n"

    fitAnalysisQuestion = "Is this candidate fit for the job description mention above? Give detailed ananlysis"    
    return startCandidateCV + str(candidateCV) + endCandidateCV + startJobDescription + str(jobDescription) + endJobDescription + fitAnalysisQuestion


def getChatGPTResponse(query):
    return query


def extractTextFromPDF(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ''
    for page_number in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_number]
        text += page.extract_text()
    return text
