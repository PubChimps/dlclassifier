from cloudant import Cloudant
from flask import Flask, render_template, request, jsonify
import atexit
import os
import json
import re
from watson_machine_learning_client import WatsonMachineLearningAPIClient


app = Flask(__name__, static_url_path='')

db_name = 'mydb'
client = None
db = None

if 'VCAP_SERVICES' in os.environ:
    vcap = json.loads(os.getenv('VCAP_SERVICES'))
    print('Found VCAP_SERVICES')
    if 'cloudantNoSQLDB' in vcap:
        creds = vcap['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)
elif "CLOUDANT_URL" in os.environ:
    client = Cloudant(os.environ['CLOUDANT_USERNAME'], os.environ['CLOUDANT_PASSWORD'], url=os.environ['CLOUDANT_URL'], connect=True)
    db = client.create_database(db_name, throw_on_exists=False)
elif os.path.isfile('vcap-local.json'):
    with open('vcap-local.json') as f:
        vcap = json.load(f)
        print('Found local VCAP_SERVICES')
        creds = vcap['services']['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)

# On IBM Cloud Cloud Foundry, get the port number from the environment variable PORT
# When running this app on the local machine, default the port to 8000
port = int(os.getenv('PORT', 8000))

@app.route('/')
def root():
    return app.send_static_file('index.html')

# /* Endpoint to greet and add a new visitor to database.
# * Send a POST request to localhost:8000/api/visitors with body
# * {
# *     "name": "Bob"
# * }
# */
@app.route('/api/visitors', methods=['GET'])
def get_visitor():
    if client:
        return jsonify(list(map(lambda doc: doc['name'], db)))
    else:
        print('No database')
        return jsonify([])

# /**
#  * Endpoint to get a JSON array of all the visitors in the database
#  * REST API example:
#  * <code>
#  * GET http://localhost:8000/api/visitors
#  * </code>
#  *
#  * Response:
#  * [ "Bob", "Jane" ]
#  * @return An array of all the visitor names
#  */
@app.route('/api/visitors', methods=['POST'])
def put_visitor():
    user = request.json['name']
    data = {'name':user}
    if client:
        my_document = db.create_document(data)
        data['_id'] = my_document['_id']
        return jsonify(data)
    else:
        print('No database')
        return jsonify(data)

def parsenb(file):
    print(file)
    code = ''
    parsednb = json.loads(file)
    for j in range(len(parsednb['cells'])):
        if parsednb['cells'][j]['cell_type'] == 'code':
            code = code + ''.join(parsednb['cells'][j]['source'])
    return code

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    file_name = file.filename
    notebook = str(file.read().decode('UTF-8'))
    data = {'notebook': notebook}
    #if client:
        #my_document = db.create_document(data)
        #data['_id'] = my_document['_id']
    returnstring = ''
    if 'wnlc' in request.form:
            file = open('dlwords.txt', 'r')
            words = file.read().split()
            bag = []
            for w in words:
                bag.append(parsenb(notebook).count(w))
            bag = [bag]
            m = {'values': bag}
            endpoint = 'https://us-south.ml.cloud.ibm.com/v3/wml_instances/b07b565e-1dea-481a-8427-ca86b142271b/deployments/0030b4c9-a084-491a-98b0-dc06bc807733/online'
            wml_credentials = {
                "apikey": "ez9iIZqgjrmDch2Masvn-PPONgr5JkxYHoaHvSSdd2F-",
                "iam_apikey_description": "Auto-generated for key 88d33208-48dc-427e-a5af-b418c521795b",
                "iam_apikey_name": "wdp-writer",
                "iam_role_crn": "crn:v1:bluemix:public:iam::::serviceRole:Writer",
                "iam_serviceid_crn": "crn:v1:bluemix:public:iam-identity::a/2645902d64b933b58d39837cd4e91c09::serviceid:ServiceId-f37d1930-1057-4c75-8106-364f99dfc181",
                "instance_id": "b07b565e-1dea-481a-8427-ca86b142271b",
                "url": "https://us-south.ml.cloud.ibm.com"
            }
            wmlclient = WatsonMachineLearningAPIClient( wml_credentials )
            results = wmlclient.deployments.score(endpoint, m)
            topclass = results['values'][0][1][0]

            returnstring = 'your top framework is:<br>'
            if topclass == 0:
                returnstring = returnstring + 'pytorch<br><br>'
            elif topclass == 1:
                returnstring = returnstring + 'tensorflow<br><br>'
            returnstring = returnstring + str(results)
    return returnstring



@atexit.register
def shutdown():
    if client:
        client.disconnect()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
