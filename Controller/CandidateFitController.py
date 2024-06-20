from flask import Blueprint, request, jsonify, make_response
from Service.CandidateFitService import candidateFitAnalysis, getReport, resourceNotFound

candidateFitController = Blueprint('candidateFitController', __name__)

@candidateFitController.route("/analysis", methods=['POST'])
def candidateFitAnalysisEndpoint():
    reqForCandidateCompare = request.args.get('reqForCandidateCompare')
    if not reqForCandidateCompare:
        return jsonify({'error': 'reqForCandidateCompare param is missing in the query parameters'}), 400

    candidateCV1 = request.files.get('candidateCV1')
    candidateCV2 = request.files.get('candidateCV2')
    jobDescription = request.files.get("jobDescription").read()

    result = candidateFitAnalysis(reqForCandidateCompare, candidateCV1, candidateCV2, jobDescription)
    return jsonify(result), 200

@candidateFitController.route("/report")
def getReportEndpoint():
    jobId = request.args.get('jobId')
    result = getReport(jobId)
    return jsonify(result), 200

@candidateFitController.errorhandler(404)
def resourceNotFoundEndpoint(e):
    result = resourceNotFound(e)
    return make_response(jsonify(result), 404)
