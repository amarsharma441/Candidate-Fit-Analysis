import os
import json
import boto3
import PyPDF2
from boto3.dynamodb.conditions import Key
from openai import OpenAI

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')  # DynamoDB resource
jobTable = dynamodb.Table('job')  # DynamoDB table
s3Client = boto3.client('s3')  # S3 client
s3Bucket = 'cv-transient-data'  # S3 bucket name
sqsClient = boto3.client('sqs')  # SQS client
sqsQueueName = 'ChatGPTProcessQueue'  # SQS queue name

def fetchChatGPTResponseByJobId(jobId):
    """
    Fetch ChatGPT response by job ID from DynamoDB and S3.
    
    Args:
        jobId (str): The job ID to fetch the response for.
    
    Returns:
        dict: A dictionary containing the status code and response body.
    """
    localFilePath = '/tmp/chatGPTResFile.txt'
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
        if os.path.exists(localFilePath):
            os.remove(localFilePath)


def createCandidateFitAnalysisQuery(candidateCV, jobDescription):
    """
    Create a query for candidate fit analysis based on the CV and job description.
    
    Args:
        candidateCV (str): The candidate's CV text.
        jobDescription (str): The job description text.
    
    Returns:
        str: The formatted query for fit analysis.
    """
    startCandidateCV = "\nSTART CANDIDATE CV\n"
    endCandidateCV = "\nEND CANDIDATE CV\n"
    startJobDescription = "\nSTART JOB DESCRIPTION\n"
    endJobDescription = "\nEND JOB DESCRIPTION\n"
    fitAnalysisQuestion = "Is this candidate fit for the job description mentioned above? Provide detailed analysis"
    
    return f"{startCandidateCV}{candidateCV}{endCandidateCV}{startJobDescription}{jobDescription}{endJobDescription}{fitAnalysisQuestion}"


def createCandidateCompareAnalysisQuery(candidateCV1, candidateCV2, jobDescription):
    """
    Create a query for comparing two candidates against a job description.
    
    Args:
        candidateCV1 (str): The first candidate's CV text.
        candidateCV2 (str): The second candidate's CV text.
        jobDescription (str): The job description text.
    
    Returns:
        str: The formatted query for candidate comparison.
    """
    startCandidateCV = "\nSTART {candidate} CANDIDATE CV\n"
    endCandidateCV = "\nEND {candidate} CANDIDATE CV\n"
    startJobDescription = "\nSTART JOB DESCRIPTION\n"
    endJobDescription = "\nEND JOB DESCRIPTION\n"
    candidateCompareAnalysisQuestion = "Compare candidates against the provided job description. Provide detailed analysis"
    
    candidate1 = startCandidateCV.format(candidate="1st") + candidateCV1 + endCandidateCV.format(candidate="1st")
    candidate2 = startCandidateCV.format(candidate="2nd") + candidateCV2 + endCandidateCV.format(candidate="2nd")
    
    return f"{candidate1}{candidate2}{startJobDescription}{jobDescription}{endJobDescription}{candidateCompareAnalysisQuestion}"


def getChatGPTResponse(queryText):
    """
    Get a response from OpenAI's ChatGPT based on the provided query text.
    
    Args:
        queryText (str): The query text to send to ChatGPT.
    
    Returns:
        dict: The response from ChatGPT.
    """
    openAIClient = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = openAIClient.Completion.create(
        messages=[
            {
                "role": "user",
                "content": queryText,
            }
        ],
        model="gpt-3.5-turbo",
    )
    return response


def extractTextFromPDF(pdfFile):
    """
    Extract text from a PDF file.
    
    Args:
        pdfFile (file-like object): The PDF file to extract text from.
    
    Returns:
        str: The extracted text from the PDF.
    """
    pdfReader = PyPDF2.PdfReader(pdfFile)
    text = ''
    for pageNumber in range(len(pdfReader.pages)):
        page = pdfReader.pages[pageNumber]
        text += page.extract_text()
    return text
