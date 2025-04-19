from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate ,login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.conf import settings
import os
import assemblyai as aai
from google import genai
import yt_dlp
from .models import BlogPost
from django.contrib import messages

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'invalid data sent'}, status= 400)

        # Get YT Title 
        title = yt_title(yt_link)
        audio = download_mp3(yt_link)

        # Get Transcript
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': "Failed to get transcript"}, status=500)          

        # Use openai to generate the blog
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': "Failed to generate blog article"}, status=500)  

    
        # Save Blog article to database
        new_blog_article = BlogPost.objects.create(
            user = request.user,
            youtube_title = title,
            youtube_link = yt_link,
            generated_content = blog_content
        )

        new_blog_article.save()
        
        return JsonResponse({'content': blog_content})
        
        # Return Article as a response
        return JsonResponse({'content':yt_link})

    else:
        return JsonResponse({'error': 'invalid request method'}, status= 405)
    
def yt_title(url):
    ydl_opts = {
        'quiet': True,  # Suppress output
        'no_warnings': True,  
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get('title', 'Title not found')
    
def download_mp3(link):
    FFMPEG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg')
    print(FFMPEG_PATH)
    MEDIA_FOLDER = "./media"
    ydl_opts = {
        'format': 'bestaudio/best',  # Get the best quality audio
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  # Extract audio using FFmpeg
            'preferredcodec': 'mp3',  # Convert to MP3 format
            'preferredquality': '192',  # Audio quality
        }],
        'outtmpl': os.path.join(MEDIA_FOLDER, '%(title)s.%(ext)s'),  # Save file as video title
        'ffmpeg_location': FFMPEG_PATH,  # Update this if FFmpeg is not in PATH
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(link, download=True)
        downloaded_file = ydl.prepare_filename(info_dict)

        
        # Replace possible formats with .mp3
        mp3_file_path = downloaded_file.replace('.webm', '.mp3').replace('.m4a', '.mp3')
        file_path = os.path.abspath(mp3_file_path)  # Get absolute path
        # base, ext = os.path.splitext(file_path)
        # abs_path = os.path.abspath(out_file)
        # base, ext = os.path.splitext(out_file)
        # newfile = base + '.mp3'
        # os.rename(file_path, newfile)
        filename = os.path.basename(file_path)
        file = './media/' + filename
        return file

def get_transcription(link):
    aai.settings.api_key = "96f43b19ec7742dc9ad016623938ce8a"

    # Step 2: Upload the File to AssemblyAI (Required for Local Files)
    audio_file = download_mp3(link)
    # upload_url = aai.upload(audio_file)

    # transcript = transcriber.transcribe(upload_url)

    transcriber = aai.Transcriber()

    transcript = transcriber.transcribe(audio_file)
    # transcript = transcriber.transcribe("./my-local-audio-file.wav")
    return transcript.text

def generate_blog_from_transcription(transcription):

    client = genai.Client(api_key="AIzaSyDPBzG5-PeRyY52LX3MjQRpsvUftjCp3YU")

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Based on the following transcript from a youtube video, write a brief and precise blog article, write it based on the transcript, but do not make it look like a youtube video, make it look like a proper blog articleL:\n\n{transcription}\n\nArticle.",
    )

    if response.text.startswith('#'):
        # Remove ##
        new_response = response.text[2:]
        return new_response
    else:
        return response

    # return new_response

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, 'all-blogs.html', {'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        redirect('/')

def youtube_downloader(request, output_folder="C:/Users/umars/Downloads"):
    if request.method == "POST":
        Youtube_url = request.POST['video-downloader']
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',  # Downloads best video & audio quality
            'merge_output_format': 'mp4',         # Ensures MP4 format
            'outtmpl': f'{output_folder}/%(title)s.%(ext)s' # Save as "downloads/video_title.mp4"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if len(Youtube_url) >= 10:
                ydl.download([Youtube_url])
                messages.success(request, "Video has been downloaded successfully!")
                return redirect("/youtube-downloader")
            else:
                messages.error(request, "Video has failed to download")
                return redirect("/youtube-downloader")

    return render(request, 'video_downloader.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Problem Creating Account'
                return render(request, 'signup.html', {'error_message': error_message})
        else:
            error_message = 'passwords do not match'
            return render(request, 'signup.html', {'error_message': error_message})
    return render(request, 'signup.html')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error_message', error_message})
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('/')