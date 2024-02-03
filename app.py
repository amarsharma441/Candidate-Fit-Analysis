from flask import Flask, jsonify, make_response
from Handlers.CandidateFit import candidateFit

app = Flask(__name__)

@app.route("/")
def hello_from_app():
    return jsonify(message='Hello from Candidate Fit Analysis App!')

app.register_blueprint(candidateFit, url_prefix='/candidateFit')

@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)

if __name__ == '__main__':
    app.run()