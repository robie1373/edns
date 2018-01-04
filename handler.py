import json
import os
import boto3
import botocore
import socket
import datetime

# ToDo: find out what kind of event the guys want to trigger this. When someone tries to donwload the file? (cloudfront type trigger)
# or, on a timer. (timer trigger)

# ToDo: make sure permissions permit the file to be downloaded by the gateways.

domname = "vpneast.aws.cms.gov"
filename = 'vpneastIPs.txt'
header = 'type=ip'
max_age_hours = 24
try:
    bucketname = os.environ.get('BUCKET_NAME')
    print "Bucket name: "
    print bucketname
except:
    print "could not look up bucket name in environment. [handler.py:8]"

s3 = boto3.resource('s3')
s3client = boto3.client('s3')

def execute(event, context):
    currentIPs          = run_lookup(domname)
    oldList             = retrieve_current_list(bucketname, filename)

    array_of_ips        = file_to_array(oldList)
    results_dict        = list_to_dict(array_of_ips)
    last24h_dict        = age_out_list(results_dict)
    # put for loop here around updatelist() to allow for multi-ip lookup.
    # update run_lookup() to grab 2 IPs

    newList             = updatelist(currentIPs, last24h_dict)
    write_status        = write_new_list(bucketname, filename, newList)
    permission_status   = set_permissions(bucketname, filename)

    body = {
        "currentResult": currentIPs,
        "write_status": write_status,
        "permission_status": permission_status,
        "input": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response

def run_lookup (domname):
    try:
        print("Looking up " + domname)
        return socket.gethostbyname_ex(domname)[2]
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
        currentList = "type=ip"
        return currentList

def file_to_array(oldList):
    #print "Entering file_to_array"
    newArray = []
    oldArray = oldList.split("\n")[1:]
    #print("[file_to_array] oldArray: " + repr(oldArray))
    for line in oldArray:
        #print("[file_to_array] newArray: " + repr(newArray))
        #print("[#file_to_array] line - " + line)
        temp_line_aray = line.split(" ", 2)
        newArray.append((temp_line_aray[0], temp_line_aray[2]))
    b = newArray[::-1]
    return newArray

def list_to_dict(newArray):
    #print "Entering list_to_dict"
    d = {}
    if len(newArray) > 0:
        for line in newArray:
            #print("line - " + repr(line))
            d[line[0]] = line[1]
            #print(d)
    return d

def age_out_list(ip_dict):
    old_ips = []
    #print "Entering age_out_list"
    #print("ip_dict: " + repr(ip_dict))
    for key, value in ip_dict.iteritems():
        #print repr(value)
        if datetime.datetime.strptime(value, "\"%Y-%m-%d %H:%M:%S.%f\"") > (datetime.datetime.utcnow() - datetime.timedelta(hours = max_age_hours)):
            print(key + " found at " + repr(value) + " is younger than " + str(max_age_hours) + " hours. Keeping it.")
        else:
            print(key + " found at " + repr(value) + " is older than " + str(max_age_hours) + " hours. Dropping it.")
            old_ips.append(key)
    for key in old_ips:
        ip_dict.pop(key, None)
    return ip_dict

def updatelist(currentIPs, results_dict):
    #print "Entering updatelist"
    newOutput = "type=ip"
    print "All times are UTC"
    print currentIPs
    for currentIP in currentIPs:
        print currentIP
        results_dict[currentIP] = datetime.datetime.utcnow().isoformat(' ')

    for key, value in results_dict.iteritems():
        try:
            newOutput = newOutput + "\n\"" + key + "\" \"vpneast.aws.cms.gov " + value + "\""
        except Exception as e:
            print e
            continue
    #print("#updatelist - newList: " + newOutput)
    return newOutput

def write_new_list(bucket, filename, newList):
    #print "Entering write_new_list"
    try:
        print("[handler.py#write_new_list]: attempting to write file to s3 bucket " + bucketname)
        #output = s3.Bucket(bucket).put_object(Key=filename, Body=newList)
        output = s3.Object(bucket, filename).put(Body=newList)
        print output
        print "[handler.py#write_new_list]: Successfully wrote to s3"
        #print("[handler.py#write_new_list]: " + newList)
        return {"write_status": "success", "result": newList}
    except Exception as write_error:
        print "Error writing file. [handler.py#write_new_list]"
        print write_error
        return {"write_status": "failure"}

def set_permissions(bucket, filename):
    try:
        print("Attempting to set permissions of file to public-read")
        output = s3client.put_object_acl(ACL='public-read', Bucket=bucket, Key=filename)
        return {"permission_status": "success"}
    except Exception as acl_error:
        print "Error setting permissions"
        print acl_error
        return {"permission_status": "failure"}
