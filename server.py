%%writefile server.py
# A Python server that takes submissions, runs them through a pretrained model, and sends
# them to the front end through a websocket.
from flask import Flask, render_template, request
from flask_socketio import SocketIO

from flask_cors import CORS, cross_origin

import json

import torch
from torch.nn.utils.rnn import pad_sequence

import numpy as np
import sklearn.decomposition as skd
pca = skd.PCA(n_components=2, whiten=True, svd_solver='full')

# Model
import MCW_rec
model = None

from MCW_text_to_input import textToInput
PAD_INDEX = 112

import sklearn.cluster as cluster

import zipfile

import asyncio

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gfndgljhgmfdsjgclsrugbr'

socketio = SocketIO(app)

@app.route('/')
@cross_origin()
def sessions():
  return render_template('index.html')

def messageRecieved(methods=['GET', 'POST']):
  print("message rcv'd by front end")

@socketio.on('connectionEvent')
def handle_connection(msg, methods=['GET', 'POST']):
  print("rcv'd event: " + str(msg))

# For clustering.
feature_array = []

# Send the full set of clustered submissions to the front end.
def toFrontEnd(d):
  socketio.emit('new_data', json.dumps(d))

def process_zip(files):
  try:
    print('processing zip')
    contents = []
    correctness = []
    features = []
    # If a file's contents are empty, do not upload it.
    # If a file's name contains 'incorrect', label it as incorrect.
    # Otherwise, label it as correct
    for file in files:
      if (file[1][-1] != '/'):
        txt = file[0].decode('utf-8')
        inp = textToInput(txt)
        if (inp):
          contents.append(txt)
          features.append(torch.tensor(inp))
          correctness.append(1 if 'incorrect' not in file[1] else 0)
    # Extract features
    print('features')
    features = pad_sequence(features, padding_value=PAD_INDEX, batch_first=True)
    features = model.extract_features(features)
    # PCA plot
    print('coords')
    coords = pca.fit_transform(features)
    # Clustering
    print('clustering')
    c = cluster.OPTICS()
    c.fit(features)
    optics = c.labels_
    c = cluster.DBSCAN()
    c.fit(features)
    dbscan = c.labels_
    # To return
    print('returning')
    to_return = []
    for c, co, cor, o, db in zip(contents, coords, correctness, optics, dbscan):
      data = {'x': float(co[0]), 'y': float(co[1]), 'text': c, 'schemes': {}}
      data['schemes']['correctness'] = int(cor)
      data['schemes']['OPTICS'] = int(o)
      data['schemes']['DBSCAN'] = int(db)
      to_return.append(data)
    to_return = {"data":to_return}
    toFrontEnd(to_return)
  except Exception as e:
    print('Error')
    print(e)
    return {"Error": str(e)}


@app.route('/zip', methods=['GET', 'POST'])
@cross_origin()
def uploadZip():
  try:
    zipFile = request.files['zipFile']
    fileLike = zipFile.stream._file
    zipObj = zipfile.ZipFile(fileLike)
    fileNames = zipObj.namelist()
    files = [(zipObj.open(n).read(), n) for n in fileNames]
    process_zip(files)
    return {"Recieved file": "True"}
  except Exception as e:
    print('Error')
    print(e)
    return {"Error": str(e)}

import threading

# cd C:\Users\Matthew C Weston\Desktop\sql-teaching-master\MCW_onlineServer
# python server.py
if __name__ == '__main__':
  # Import the trained model
  model = MCW_rec.FeatureExtractor(PAD_INDEX+1, 32, 64, 2, pad_index=PAD_INDEX, layers=4, dropout=.4, bidirectional=True)
  model.load('model')
  #
  socketio.run(app, debug=True, port=2020)