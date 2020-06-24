# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START gae_python37_render_template]
import datetime
import requests
from flask import Flask, render_template, redirect, request, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileRequired, FileAllowed
from werkzeug.utils import secure_filename
import uuid
from google.cloud import storage
from google.cloud import firestore
import os

app = Flask(__name__)
app.secret_key = b'_5#y2L"Fsdadfnosa4Q8z\n\xec]/'
bucket_name = 'rapid-spider-280019.appspot.com'
db = firestore.Client()

class StartForm(FlaskForm):
    url = StringField('url', validators=[DataRequired()])
    cookie = StringField('cookie', validators=[DataRequired()])

class TiltForm(FlaskForm):
    photo = FileField(validators=[FileRequired(), FileAllowed(['jpg','png'], 'Images only!')])
    message = StringField('message', validators=[DataRequired()])
    name = StringField('name', validators=[DataRequired()])

class LeaderboardForm(FlaskForm):
    one = StringField('First place', validators=[DataRequired()])
    two = StringField('Second place', validators=[DataRequired()])
    three = StringField('Third place', validators=[DataRequired()])
    four = StringField('Fourth place', validators=[DataRequired()])
    five = StringField('Fifth place', validators=[DataRequired()])

def log():
    url = app.config.url
    cookies = dict(npt=app.config.cookie)
    res = requests.get(url, cookies=cookies)
    if res.status_code != 200:
        pass
    return res.json()

@app.route('/')
def root():
    # For the sake of example, use static information to inflate the template.
    # This will be replaced with real information in later steps.
    now = datetime.datetime.utcnow()
    if True or (now.weekday() == 3 and now.hour >= 23 and now.minute >= 30) or (now.weekday() == 4 and now.hour <= 6):
        tilt_ref = db.collection(u'tilt').document(u'active').get()
        if tilt_ref.exists:
            tilt = tilt_ref.to_dict()
        else:
            tilt = None
        return render_template('index.html', tilt=tilt)
    else:
        next_thursday = now + datetime.timedelta((3 - now.weekday())%7)
        next_thursday_string = next_thursday.strftime('%b %d, %Y 19:30:00')
        
        leader_ref = db.collection(u'game').document(u'leaderboard').get()
        if leader_ref.exists:
            leaderboard = leader_ref.to_dict()
        else:
            leaderboard = None
        return render_template('index.html', next_thursday=next_thursday_string, leaderboard=leaderboard)
    return render_template('index.html')




@app.route("/admin/1234567890/upload", methods=('GET', 'POST'))
def upload_tilt():
    form = TiltForm()
    if form.validate_on_submit():
        f = form.photo.data
        filename = secure_filename(f.filename)
        message = form.message.data
        name = form.name.data
        filepath = 'https://storage.cloud.google.com/{}/{}'.format(bucket_name, filename)
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_file(request.files[form.photo.name])

        doc_ref = db.collection(u'tilt').document(u'active')
        doc_ref.set({
            u'photo': filepath,
            u'message': message,
            u'name': name
        })
        
        return redirect('/')
    return render_template('admin-tilt.html', form=form)

@app.route('/admin/1234567890/start', methods=('GET', 'POST'))
def start():
    form = StartForm()
    if form.validate_on_submit():
        url = form.url.data
        cookie = form.cookie.data

        game_ref = db.collection(u'game').document(u'active')
        game_ref.set({
            u'url': url,
            u'cookie': cookie
        })

        return redirect('/')
    return render_template('admin-start.html', form=form)


@app.route('/admin/1234567890/leader', methods=('GET', 'POST'))
def leader():
    form = LeaderboardForm()
    if form.validate_on_submit():
        one = form.one.data
        two = form.two.data
        three = form.three.data
        four = form.four.data
        five = form.five.data

        leader_ref = db.collection(u'game').document(u'leaderboard')
        leader_ref.set({
            u'one': one,
            u'two': two,
            u'three': three,
            u'four': four,
            u'five': five,
        })

        return redirect('/')
    return render_template('admin-leader.html', form=form)

if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
# [START gae_python37_render_template]
