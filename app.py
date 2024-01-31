from flask import Flask, jsonify, make_response
from Handlers.CandidateFit import candidate_fit

app = Flask(__name__)

@app.route("/")
def hello_from_root():
    return jsonify(message='Hello from root!')

app.register_blueprint(candidate_fit, url_prefix='/candidateFit')

@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)

if __name__ == '__main__':
    app.run()