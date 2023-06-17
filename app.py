from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from flask import Flask, request, jsonify, redirect, Response 
import json
import uuid
import time
from array import *

# Connect to our local MongoDB
client = MongoClient('mongodb://localhost:27017/')

# Choose database
db = client['InfoSys']

# Choose collections
students = db['Students']
users = db['Users']

# Initiate Flask App
app = Flask(__name__)

users_sessions = {}


def create_session(username):
    user_uuid = str(uuid.uuid1())
    users_sessions[user_uuid] = (username, time.time())
    return user_uuid  

def is_session_valid(user_uuid):
    return user_uuid in users_sessions

# Create User Endpoint
@app.route('/createUser', methods=['POST'])
def create_user():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "username" in data or not "password" in data:
        return Response("Information incomplete",status=500,mimetype="application/json")

    users.find({"username":data["username"]}, {"password":data["password"]}) # Check username / password
    if users.find({"username":data["username"]}).count() == 0 :              # If the user does not exist.
        user = {"username": data['username'], "password": data['password']}
        # Add user to the "Users" collection
        users.insert_one(user)
        return Response(data['username']+" was added to the MongoDB", status=200,mimetype='application/json')
    else:
        return Response("A user with the given credentials already exists", status=400 ,mimetype='application/json')


# User Login
@app.route('/login', methods=['POST'])
def login():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "username" in data or not "password" in data:
        return Response("Information incomplete",status=500,mimetype="application/json")

    if users.find({'$and':[{"username":data["username"]},{"password":data["password"]} ]}).count() !=0  :
        user_uuid = create_session(data['username'])
        res = {"uuid": user_uuid, "username": data['username']}
        return Response(json.dumps(res),status=200,mimetype='application/json')
    else:
        return Response("Wrong username or password.",status=400,mimetype='application/json')
        

# Get info based on undergraduate-email 
@app.route('/getStudent', methods=['GET'])
def get_student():
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "email" in data:
        return Response("Information incomplete",status=500,mimetype='application/json')
    
    uuid = request.headers.get('Authorization')
    email = request.args.get('email')
    if email == None :
        return Response("Bad request", status=500, mimetype='application/json')
    if is_session_valid(uuid) == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    if is_session_valid(uuid) == True:
        student = students.find_one({"email": email})
        if student != None : 
            student = {'name':student["name"], 'email':student["email"], 'yearOfBirth':student["yearOfBirth"], 'address':student["address"]}
            return Response(json.dumps(student), status=200, mimetype='application/json')
        if student == None:
            return Response('No student was found by that email: '+email,status=400,mimetype='application/json') 


# Get 30-years old students
@app.route('/getStudents/thirties', methods=['GET'])
def get_students_thirty():
    uuid = request.headers.get('Authorization')
    if is_session_valid(uuid) == False  :
        return Response("Student was not authendicated ",status=401,mimetype='application/json')
    if is_session_valid(uuid) == True :
        all_students = students.find({"yearOfBirth":1991 }) #Thirty years old relative to current date (2021)
        student = []
        if all_students != None :
            for i in all_students:
                i['_id']=None
                student.append(i)
            return Response(json.dumps(student), status=200, mimetype='application/json')  
        if all_students == None : 
            return Response("No student found at the age of 30 ",status=400,mimetype='application/json')   

# Get students that are at least 30-years old
@app.route('/getStudents/oldies', methods=['GET'])
def get_students_thirty_and_beyond():
    uuid = request.headers.get('Authorization')
    if is_session_valid(uuid) == False:
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    if is_session_valid(uuid) == True:
        student = students.find({"yearOfBirth": {'$lte' : 1991 }}) #Again relative to year: 2021
        if student != None :
            Students = []
            for i in student:
                i['_id'] = None
                Students.append(i)
            return Response(json.dumps(Students), status=200, mimetype='application/json')
        else :
            return Response("No student found older than thirty years old",status=400,mimetype='application/json')
   

# Get student with submitted location
@app.route('/getStudentAddress', methods=['GET'])
def get_student_Address():
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "email" in data:
        return Response("Information incomplete",status=500,mimetype='application/json')
    uuid = request.headers.get('Authorization')
    email = request.args.get('email')
    if email == None :
        return Response("Bad request", status=500, mimetype='application/json')
    if is_session_valid(uuid) == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    if is_session_valid(uuid) == True:
        student = students.find_one({'$and': [{"email":email}, {'address': {'$exists': True}} ] })
        if student  != None:        
            student = {'name':student["name"], 'street':student["address"][0]["street"], 'postcode':student["address"][0]["postcode"]} #Example: 'postcode' name to be displayed after utillization , address is an array of objects so : [array][Object:0][key-value-inside-the-object] -> ["address"][0]["postcode"]  
            return Response(json.dumps(student), status=200, mimetype='application/json')
        if student == None:
            return Response('No student was found by that email: '+email+' or with a corresponding address',status=400,mimetype='application/json')



# Delete student based on email
@app.route('/deleteStudent', methods=['DELETE'])
def delete_student():
    uuid= request.headers.get('Authorization')
    email = request.args.get('email')
    if email == None :
        return Response("Bad request", status=500, mimetype='application/json')
    if is_session_valid(uuid) == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    if is_session_valid(uuid) == True:
        student = []
        student = students.find_one({"email": email})
        if student != None:
            msg = (student['name']+' was deleted.')
            students.delete_one({"email": email})
            return Response(msg, status=200, mimetype='application/json')
        else:
            msg = ('No student found by the corresponding email : '+email)
            return Response(msg,status=400,mimetype='application/json')



# Update curriculum based on student-email
@app.route('/addCourses', methods=['PATCH'])
def add_courses():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "email" in data:
        return Response("Information incompleted",status=500,mimetype="application/json")
    uuid = request.headers.get('Authorization')
    email = request.args.get('email')
    if is_session_valid(uuid) == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    if is_session_valid(uuid) == True :
        student = students.find({"email": email})
        if student == None: 
              return Response('Corresponding email was not found in the system',status=400,mimetype='application/json')
        try:  
              
              student = students.update_one({"email":email},
              {"$set": 
              {
                   "courses":  data["courses"]                                                                                                                                                         
              }
              }) 
              
              msg=('Courses were added successfully')
              return Response(msg, status=200, mimetype='application/json')
        except Exception as e:
              return Response('Courses could not be added',status=500,mimetype='application/json')
        
    

# Get succesfully passed subjects based on email
@app.route('/getPassedCourses', methods=['GET'])
def get_courses():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "email" in data:
        return Response("Information incomplete",status=500,mimetype="application/json")
    uuid = request.headers.get('Authorization')
    email = request.args.get('email')
    if is_session_valid(uuid) == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    if is_session_valid(uuid) == True :
        student = students.find_one({'$and': [{"email":email}, {'courses': {'$exists': True}} , {'courses': {'$gte': 5}} ] })
        if student != None:
             
             student = {'name':student["name"] }
             return Response(json.dumps(student), status=200, mimetype='application/json')
        if student == None: 
            return Response('No student found matching the email given or student has not aquired the required mark to succeed in at least one course', status=500,mimetype='application/json')
    
    

# Flask service, debug-mode = ON , port 5000
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
