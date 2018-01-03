import json
import os
import boto3
import botocore
import socket
import datetime

domname = "vpneast.aws.cms.gov"
filename = 'vpneastIPs.txt'
header = 'type=ip'
try:
    bucketname = os.environ.get('BUCKET_NAME')
    print "Bucket name: "
    print bucketname
except:
    print "could not look up bucket name in environment. [handler.py:8]"

s3 = boto3.resource('s3')

def execute(event, context):
    currentIP = run_lookup(domname)
    oldList = retrieve_current_list(bucketname, filename)
    newList = updatelist(currentIP, oldList)
    newList = uniq_list(newList)
    newList = age_out_list(newList)
    status = write_new_list(bucketname, filename, newList)

    body = {
        "currentResult": currentIP,
        "status": status,
        "input": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response

def updatelist(currentIP, oldlist):
    delim = '\n'
    newLine = currentIP + " vpneast.aws.cms.gov " + str(datetime.datetime.now())
    newList = delim.join( (oldlist, newLine) )
    print("#updatelist - newList: " + newList)
    return newList

def line_to_dict(line):
    a = line.split(" ", 2)
    d = { a[0]: a[2] }
    return a

def list_to_dict(newList):
    d = {}
    for line in newList:
        print("line - " + line)
        a = line.split(" ", 2)
        print("a - " + a)
        d[a[0]] = a[2]
        print("d - " + d)

def uniq_list(newList):
    print "todo: uniq_list"
    list_to_dict(newList)
    return newList

def age_out_list(newList):
    print "todo: age_out_list"
    return newList

def run_lookup (domname):
    try:
        return socket.gethostbyname(domname)
    except:
        print "Unable to run lookup. [handler.py#run_lookup:35]"

def retrieve_current_list(bucket, filename):
    try:
        print("Getting current list [handler.py#retrieve_current_list]")
        #currentList = s3.Object.get(bucket, filename)
        currentList = s3.Object(bucket, filename).get()['Body'].read()
        return currentList
    except Exception as read_error:
        print read_error
        print "unable to find old list. Creating new, empty list. [handler.py#retrieve_current_list:41]"
        currentList = "type=ip\n"
        return currentList


def write_new_list(bucket, filename, newList):
    try:
        print "[handler.py#write_new_list]: write file to s3"
        #output = s3.Bucket(bucket).put_object(Key=filename, Body=newList)
        output = s3.Object(bucket, filename).put(Body=newList)
        print output
        print "[handler.py#write_new_list]: wrote to s3"
        print("[handler.py#write_new_list]: " + newList)
        return {"status": "success"}
    except Exception as write_error:
        print "Error writing file. [handler.py#write_new_list]"
        print write_error
        return {"status": "failure"}
