# -*- coding: utf-8 -*-

import os
import subprocess
import stat
import shutil
import boto3
from botocore.vendored import requests
import datetime
import logging

print('Loading function')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = boto3.session.Session()
lex = boto3.client('lex-runtime', region_name='us-east-1')



lambda_tmp_dir = '/tmp' # Lambda fuction can use this directory.
image_path = "{0}/{1}".format(lambda_tmp_dir, "images")
video_path = "{0}/{1}".format(lambda_tmp_dir, "video")
audio_name = "bookacar.mp4"
local_source_audio = "{0}/downloaded.mp4".format(lambda_tmp_dir)
output_file = "{0}/outout.wav".format(lambda_tmp_dir)


def is_lambda_runtime():
    return True if "LAMBDA_TASK_ROOT" in os.environ else False

if is_lambda_runtime():
    # ffmpeg is stored with this script.
    # When executing ffmpeg, execute permission is requierd.
    # But Lambda source directory do not have permission to change it.
    # So move ffmpeg binary to `/tmp` and add permission.
    ffmpeg_bin = "{0}/ffmpeg.linux64".format(lambda_tmp_dir)
    shutil.copyfile('/var/task/ffmpeg.linux64', ffmpeg_bin)
    os.environ['IMAGEIO_FFMPEG_EXE'] = ffmpeg_bin
    os.chmod(ffmpeg_bin, os.stat(ffmpeg_bin).st_mode | stat.S_IEXEC)


def postContent(filename, userId):
    with open(filename, 'rb') as file:
        resp = lex.post_content(
            botName='BookTrip',
            botAlias='bobo',
            userId=userId,
            contentType='audio/l16; rate=16000; channels=1',
            accept='audio/mpeg',
            inputStream=file
        )
        # print(resp)
        return resp

def postText(text, userId=None):
    print('postText as %s' % userId)
    resp = lex.post_text(
        botName='BookTrip',
        botAlias='bobo',
        userId=userId,
        inputText=text
    )
    # print(resp)
    return resp

def download_audio(audio_url):
    resp = requests.get(audio_url)
    download_to = local_source_audio
    if resp.status_code==200:
        with open(download_to, "wb") as fh:
            fh.write(resp.content)
    output = subprocess.check_output(["file", local_source_audio ])
    print( str(output, "utf-8") )
    

def transcode_audio():
    print('start transcode_audio()')
    resp = subprocess.check_output([ffmpeg_bin, '-i', local_source_audio, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-y', output_file ])
    print( str(resp, "utf-8") )    
    print( str(subprocess.check_output(["file", output_file ]), "utf-8")  )

def lambda_handler(event, context):
    print(event)
    userId = "{0}:{1}".format(event["platform"], event["senderID"])
    
    if 'messageAttachments' in event:
        if event["messageAttachments"][0]["type"]=="audio":
            audio_url = event["messageAttachments"][0]["payload"]["url"]
            print("proccessing audio_url=%s" % audio_url)
            download_audio(audio_url)
            transcode_audio()
            resp = postContent(output_file, userId)
            print(resp)
            if "audioStream" in resp:
                # temporarily audioStream
                resp["audioStream"] = ""
            return resp
        else:
            print("unknown or invalid attachment")
    elif 'messageText' in event:
        text = event["messageText"]
        print('processing text=%s' % text)
        resp = postText(text, userId)
        print(resp)
        return resp
    else:
        print("unhandled exception")
        return "unhandled exception"
        
    #transcode_audio()
    #postContent()
    return "OK"
    
