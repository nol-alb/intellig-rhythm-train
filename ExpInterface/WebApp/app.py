import sys, os
from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, IntegerField
import csv
import numpy as np
import json
import audioProcess as aud
import visualization as viz

aud.hellofunc()
app = Flask(__name__,static_folder='static',
            template_folder='templates')

# Set the secret_key on the application to something unique and secret, to use session
app.secret_key = os.urandom(24)
app.debug = True
Stimarr = np.array(['G1', 'G2', 'G3', 'G4', 'G5', 'G6'])
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "POST":
        return redirect(url_for('consent'))
    return render_template('homepage.html')
@app.route('/consent', methods=['GET','POST'])
def consent():
    if request.method == "POST":
        return redirect(url_for('register'))
    return render_template('consent.html')

@app.route('/practiceplay', methods=['GET', 'POST'])
def practicePlayRoutine():
    currFolder = session['currentFolder']
    stimFolder =  'static/data/Stimuli'
    trials = os.path.join(stimFolder,currFolder)
    trialFiles = []
    plotFiles = []
    onsetFiles = []
    for f in os.listdir(trials):
        if f.endswith(".mp3"):
            trialFiles.append( os.path.join(trials, f))
        if f.endswith(".png"):
            plotFiles.append( os.path.join(trials, f))
        if f.endswith(".npy"):
            onsetFiles.append(os.path.join(trials, f))
    trialFiles.sort()
    plotFiles.sort()
    onsetFiles.sort()
    '''
    Check for the skip at beginning

    '''
    session['StimuliSize'] = len(trialFiles)
    trialFileCount = int(session["TrialFileCount"])
    audioFilePath = trialFiles[trialFileCount]
    plotFilePath = plotFiles[trialFileCount]
    onsetFilePath = onsetFiles[trialFileCount]
    onsetData = np.load(onsetFilePath)
    onsetData = onsetData.tolist()
    session['OnsetData'] = onsetData[0]
    patternData =  session['StimuliData']
    session['currentPattern'] = patternData[session['currentFolder']][trialFileCount]
    print(audioFilePath)
    print(plotFilePath)
    #Create the audio files and send the required files for practice run the routines and then go to the required exp setup
    if request.method == "POST":
        trialFileCount = trialFileCount+1
        session["IsUpload"] = "No"
        session["TrialFileCount"] = trialFileCount
        return redirect(url_for('practiceRecordRoutine'))
    else:
        return render_template('practiceplay.html',songout = audioFilePath, plotout =plotFilePath)

def saveAudio(filename):
        f = request.files['audio_data']
        outname= filename
        session["IsUpload"] = "Yes"
        with open(outname, 'wb') as audio:
             f.save(audio)
        return 0

@app.route('/practicerecord', methods=['GET','POST'])
def practiceRecordRoutine():
    if request.method == "POST":
        UploadCheck = session["IsUpload"]
        if(UploadCheck=="No"):
            fileDirectory = session['participantPath']
            filePath = os.path.join(fileDirectory, session['currentFolder'])
            currentPattern =  ''.join(str(pat) for pat in session['currentPattern'])
            fileName = filePath + '/audio/' + currentPattern + '_' + session['StimuliRepeat'] + '.wav' 
            session['RecordFilePath'] = fileName
            saveAudio(fileName)
            isExist = os.path.exists(fileName)
            return render_template('practicerecord.html')
        else:
            pattern = session['currentPattern']
            audioPath = session['RecordFilePath']
            onsetData = session['OnsetData']
            averagebeat, averagecycle,cnrt = aud.errordet(audio=audioPath,fs=44100,onset_gen=np.array(onsetData),s=pattern)
            print('PatternHere:',pattern, averagebeat)
            patternPlay = viz.errorVisualization(pattern, averagebeat)
            print('PlayPatternHere:',patternPlay)
            fileDirectory = session['participantPath']
            filePath = os.path.join(fileDirectory, session['currentFolder'])
            currentPattern =  ''.join(str(pat) for pat in session['currentPattern'])
            fileName = filePath + '/images/' + currentPattern + '_' + session['StimuliRepeat'] + '.png'
            viz.PatternErrorVisualizer(pattern,patternPlay,fileName)
            session['ImageFilePath'] = fileName
            return redirect(url_for('practicePerformanceView'))
    else:
        return render_template('practicerecord.html')


@app.route('/practiceperformance', methods=['GET','POST'])
def practicePerformanceView():
    fileName = session['ImageFilePath']
    pattern = session['currentPattern']
    audioPath = session['RecordFilePath']
    onsetData = session['OnsetData']
    averagebeat, averagecycle,cnrt = aud.errordet(audio=audioPath,fs=44100,onset_gen=np.array(onsetData),s=pattern)
    #Check if trial file count is equal to length of stimuli folder, if yes, show the block pause html else move on
    '''
    if it is the final slot then make the dashboard and thank them!
    '''
    trialFileCount = session["TrialFileCount"]
    if request.method=='POST':
        if (cnrt == 0):
            if (trialFileCount>0):
                trialFileCount = trialFileCount - 1
            else:
                trialFileCount =0
            numRep = session['StimuliRepeat']
            numRep = int(numRep)+1
            session['StimuliRepeat'] = str(numRep)
            session["TrialFileCount"] =  trialFileCount
            return redirect(url_for('practicePlayRoutine'))
        else:
            fileDirectory = session['participantPath']
            filePath = os.path.join(fileDirectory, session['currentFolder'])

            csv_file = os.path.join(filePath, 'patterns.csv')
            with open(csv_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([str(pattern),session['StimuliRepeat']])
            if(trialFileCount == int(session['StimuliSize'])):
                return redirect(url_for('blockWaitRoutine'))
            else:
                session['StimuliRepeat'] = str(1)
                return redirect(url_for('practicePlayRoutine'))
    else:
        #saveragebeat, averagecycle,cnrt = aud.errordet(audioPath,44100,onsetData,pattern)
        return render_template('practiceperformance.html', imageOut = fileName, n = cnrt)
@app.route('/blockcomplete', methods=['GET','POST'])
def blockWaitRoutine():
    cntOrder = session['OrderCount']
    #just have to change current folder in post
    if request.method=='POST':
        cntOrder = int(cntOrder)+1
        stims = session['stimuliOrder']
        print('this is stimuli:',session['stimuliOrder'] )
        session['OrderCount'] = cntOrder
        if(cntOrder>5):
            return render_template('experimentcomplete.html')
        session['currentFolder'] = stims[cntOrder]
        session["TrialFileCount"] =  str(0)
        return redirect(url_for('practicePlayRoutine'))
    else:
        return render_template('blockcomplete.html')


"""
Registration:
    To conduct registration of the participants we use the wtforms library and create a class called RegisterForm that
    stores the required registration headers and fields. We can indicate the required details we need from the participant in
    this section. 
    > We then create and app.route to a registration page which hosts methods of both GET and POST.
    > We get the form html page and will post to a trial experiment setup.
    
"""
class RegisterForm(Form):
    musician = StringField('Musician (YES/NO)', [validators.Length(min=2, max=4)])
    gender = StringField('Gender')
    instrument = StringField('If yes, Which Instrument?')
    years_of_exp = IntegerField('Years of experience (Only Number)')
    inst_of_record = StringField('Instrument you will use to tap the patterns? [Clapping, or any percussion instrument]')

@app.route('/registration', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        intTrialFileCount = 0
        session['StimuliRepeat'] = str(1)
        session['StimuliSize'] = str(0)
        session['OnsetData'] = []
        session['OrderCount'] = str(0)
        session['TrialFileCount'] = str(intTrialFileCount)
        Stimarr = np.array(['G1', 'G2', 'G3', 'G4', 'G5', 'G6'])
        participantData = dict(request.form)
        RandGen = np.load('static/data/listOfNumbers.npy')
        participantInd, RandGen = RandGen[-1], RandGen[:-1]
        np.save('static/data/listOfNumbers.npy',RandGen)
        newPath = 'static/data/experimentData/' + str(participantInd)
        session['participantIndex'] = str(participantInd)
        os.mkdir(newPath)
        # A session is used to store user specific information and required data
        session['participantPath'] = newPath
        np.random.shuffle(Stimarr)
        Stims = Stimarr
        Stims = np.insert(Stims, 0, 'Gt')
        #add the trial folderName to the beginning of the stimarr

        session['stimuliOrder'] = list(Stims)
        print(Stims)
        Stimarr = np.array(['G1', 'G2', 'G3', 'G4', 'G5', 'G6'])
        Order = session['stimuliOrder']
        session["IsUpload"] = "No"
        print(Order)
        for i in Order:
            stimFolder = os.path.join(newPath, i)
            os.mkdir(stimFolder)
            audioFiles =os.path.join(stimFolder, 'audio')
            os.mkdir(audioFiles)
            performanceFiles = os.path.join(stimFolder,'images')
            os.mkdir(performanceFiles)
            csv_file = os.path.join(stimFolder, 'patterns.csv')
            with open(csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Pattern","No_Of_Tries"])
        #Creating directories for trial images and audio
        file = 'static/data/Stimuli/patternsDictionary.json'
        with open(file, 'r') as f:
            patternData = json.load(f)
        session['StimuliData'] = patternData
        session['currentPattern'] = patternData['Gt'][0]
        session['currentFolder'] = 'Gt'
        # trialFolder =os.path.join(newPath, 'Gt')
        # os.mkdir(trialFolder)
        # audioFiles =os.path.join(trialFolder, 'audio')
        # os.mkdir(audioFiles)
        # performanceFiles = os.path.join(trialFolder,'images')
        # os.mkdir(performanceFiles)
        # csv_file = os.path.join(trialFolder/>/, 'patterns.csv')
        # with open(csv_file, 'w', newline='') as file:
        #         writer = csv.writer(file)
        # writer.writerow(["Pattern","No_Of_Tries"])

        userdata = dict(request.form)
        session['RecordFilePath'] = ''
        session['ImageFilePath'] = ''
        musician = userdata["musician"]
        instrument = userdata["instrument"]
        years_of_exp = userdata["years_of_exp"]
        inst_of_record  = userdata["inst_of_record"]
        gender = userdata["gender"]
        with open('static/data/experimentData/participants.csv', mode='a') as csv_file:
            data = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            data.writerow([str(participantInd), Order[1],Order[2],Order[3],Order[4],Order[5],Order[6],musician,instrument,years_of_exp,inst_of_record,gender,'No'])
        csv_file.close()
        
        return redirect(url_for('practicePlayRoutine'))



    return render_template('registration.html', form=form)