from flask import Flask, Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from boto3.dynamodb.conditions import Key
import boto3

bcrypt = Bcrypt()

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('users')


user = Blueprint('user', __name__)

@user.route("/register", method=['POST'])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    # Check if the username is already taken
    response = table.query(KeyConditionExpression=Key('username').eq(username))
    if response.get("Items"):
        return jsonify(error="Username already exists"), 400

    # Encrypt the password using bcrypt
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Store the user in DynamoDB
    table.put_item(Item={'username': username, 'password': hashed_password})

    return jsonify(message="Registration successful"), 201

@user.route("/hello")
def hello():
    return jsonify(message='Hello from path!')
