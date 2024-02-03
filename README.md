
# Candidate Fit Analysis
## Overview
Candidate Fit Analysis is a serverless application built on AWS to perform analysis of candidate profiles against job requirements. This application follows an event-driven serverless architecture, utilizing AWS Lambda, DynamoDB, S3, and SQS for efficient processing.

## Technologies Used
#### AWS Services: 
* Lambda: Utilized for serverless deployment, ensuring scalability and cost-effectiveness.
* API Gateway: Manages HTTP API endpoints for communication with the application.
* DynamoDB: A NoSQL database used for storing candidate fit analysis data.
* S3: Used for storing transient data and ChatGPT queries/responses.
* SQS: Enables asynchronous message processing for GPT queries, contributing to an event-driven architecture.
* IAM Roles: Defines IAM roles for Lambda functions with specific permissions to access DynamoDB, S3, and SQS.
#### Serverless Framework:
* The Serverless Framework is employed to streamline deployment and management of serverless functions on AWS.
#### Python
* boto3: AWS SDK for Python
* Flask: Web framework for handling HTTP requests
* PyPDF2: Library for working with PDF files
* openai: Python library for interfacing with OpenAI GPT models
* Werkzeug: WSGI(Web Server Gateway Interface) utility library for handling HTTP requests and responses
* markupsafe: Library for securely handling and displaying HTML content



### Serverless Functions:
* CandidateFitAnalysis:
    > Receives candidate data, generates ChatGPT queries, and stores them in an SQS queue.
    > Utilizes AWS Lambda for serverless execution.
* ProcessGPTQuery:
    > Listens to the SQS queue, retrieves ChatGPT queries, processes them, and stores the results.
    > Uses AWS Lambda for serverless execution.
    > Implements a time-to-live mechanism for result availability.

![](https://github.com/amarsharma441/Candidate-Fit-Analysis/blob/main/Assets/template-designer.png)

## Deployment
* Ensure you have the Serverless Framework installed.
* Configure your AWS credentials.
* Set the OPENAI_API_KEY environment variable.
* Deploy the application using serverless deploy.

## Usage
* Use the HTTP API endpoint (/analysis) to initiate candidate fit analysis.
* Access the analysis report using the /report endpoint with the corresponding job ID.
## Notes
* The OPENAI_API_KEY should be securely stored in the environment variable.
